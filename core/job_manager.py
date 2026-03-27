from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from core.processing import ProcessResult, ProcessingOptions, process_files_parallel

DB_PATH = Path("output") / "jobs.db"
JOBS_ROOT = Path("output") / "jobs"

JobStatus = str


@dataclass(slots=True)
class JobFileRecord:
    source_name: str
    status: str
    message: str
    file_type: str | None
    output_paths: list[str]


@dataclass(slots=True)
class ConversionJob:
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    total_files: int
    processed_files: int
    current_file: str
    target_format: str
    error: str
    workers: int
    options_json: str
    zip_path: str
    files: list[JobFileRecord]


@dataclass(slots=True)
class _QueuedJob:
    job_id: str
    payloads: list[tuple[str, bytes]]
    target_format: str
    workers: int
    options: ProcessingOptions


_jobs_lock = threading.Lock()
_job_queue: Queue[_QueuedJob] = Queue()
_worker_started = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _init_db() -> None:
    with _db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                processed_files INTEGER NOT NULL,
                current_file TEXT NOT NULL,
                target_format TEXT NOT NULL,
                error TEXT NOT NULL,
                workers INTEGER NOT NULL,
                options_json TEXT NOT NULL,
                zip_path TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                file_type TEXT,
                output_paths_json TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_job_files_job_id ON job_files(job_id)")


def _update_job_progress(job_id: str, *, processed: int, total: int, current_file: str) -> None:
    with _db_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, updated_at = ?, processed_files = ?, total_files = ?, current_file = ?
            WHERE job_id = ?
            """,
            ("processing", _now_iso(), processed, total, current_file, job_id),
        )


def _store_job_completion(job_id: str, results: list[ProcessResult], target_format: str) -> None:
    job_dir = JOBS_ROOT / job_id
    files_dir = job_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    file_records: list[JobFileRecord] = []
    for result in results:
        per_file_paths: list[str] = []
        source_stem = Path(result.source_name).stem or "file"
        source_dir = files_dir / source_stem
        source_dir.mkdir(parents=True, exist_ok=True)

        for output in result.outputs:
            output_path = source_dir / output.filename
            base = output_path.stem
            ext = output_path.suffix
            suffix = 1
            while output_path.exists():
                output_path = source_dir / f"{base}_{suffix}{ext}"
                suffix += 1
            output_path.write_bytes(output.content)
            per_file_paths.append(str(output_path))

        file_records.append(
            JobFileRecord(
                source_name=result.source_name,
                status="done" if result.success else "failed",
                message=result.message,
                file_type=result.file_type,
                output_paths=per_file_paths,
            )
        )

    zip_path = job_dir / f"converted_{job_id}_{target_format}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for record in file_records:
            for path_str in record.output_paths:
                output_path = Path(path_str)
                archive.write(output_path, arcname=output_path.name)

    with _db_connection() as conn:
        conn.execute("DELETE FROM job_files WHERE job_id = ?", (job_id,))
        for record in file_records:
            conn.execute(
                """
                INSERT INTO job_files(job_id, source_name, status, message, file_type, output_paths_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    record.source_name,
                    record.status,
                    record.message,
                    record.file_type,
                    json.dumps(record.output_paths),
                ),
            )
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, updated_at = ?, processed_files = ?, current_file = ?, error = ?, zip_path = ?
            WHERE job_id = ?
            """,
            ("done", _now_iso(), len(results), "", "", str(zip_path), job_id),
        )


def _mark_job_failed(job_id: str, error: str) -> None:
    with _db_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, updated_at = ?, current_file = ?, error = ?
            WHERE job_id = ?
            """,
            ("failed", _now_iso(), "", error, job_id),
        )


def _process_job(job: _QueuedJob) -> None:
    _update_job_progress(job.job_id, processed=0, total=len(job.payloads), current_file="")

    def on_progress(completed: int, total: int, current_name: str) -> None:
        _update_job_progress(
            job.job_id,
            processed=completed,
            total=total,
            current_file=current_name,
        )

    try:
        results = process_files_parallel(
            job.payloads,
            target_format=job.target_format,
            options=job.options,
            max_workers=job.workers,
            use_processes=False,
            progress_callback=on_progress,
        )
        _store_job_completion(job.job_id, results, job.target_format)
    except Exception as exc:
        _mark_job_failed(job.job_id, str(exc))


def _worker_loop() -> None:
    while True:
        job = _job_queue.get()
        try:
            _process_job(job)
        finally:
            _job_queue.task_done()


def _ensure_worker_started() -> None:
    global _worker_started
    if _worker_started:
        return
    _init_db()
    worker = threading.Thread(target=_worker_loop, daemon=True, name="conversion-job-worker")
    worker.start()
    _worker_started = True


def create_job(
    payloads: list[tuple[str, bytes]],
    target_format: str,
    workers: int,
    options: ProcessingOptions,
) -> str:
    _ensure_worker_started()
    job_id = uuid4().hex[:12]
    now = _now_iso()
    options_json = json.dumps(asdict(options))

    with _db_connection() as conn:
        conn.execute(
            """
            INSERT INTO jobs(
                job_id, status, created_at, updated_at, total_files, processed_files, current_file,
                target_format, error, workers, options_json, zip_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                "pending",
                now,
                now,
                len(payloads),
                0,
                "",
                target_format,
                "",
                max(1, workers),
                options_json,
                "",
            ),
        )
        for source_name, _ in payloads:
            conn.execute(
                """
                INSERT INTO job_files(job_id, source_name, status, message, file_type, output_paths_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, source_name, "pending", "", None, "[]"),
            )

    _job_queue.put(
        _QueuedJob(
            job_id=job_id,
            payloads=payloads,
            target_format=target_format,
            workers=max(1, workers),
            options=options,
        )
    )
    return job_id


def get_job(job_id: str) -> ConversionJob | None:
    _init_db()
    with _db_connection() as conn:
        job_row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if job_row is None:
            return None

        file_rows = conn.execute(
            "SELECT source_name, status, message, file_type, output_paths_json FROM job_files WHERE job_id = ?",
            (job_id,),
        ).fetchall()

    files = [
        JobFileRecord(
            source_name=row["source_name"],
            status=row["status"],
            message=row["message"],
            file_type=row["file_type"],
            output_paths=json.loads(row["output_paths_json"]),
        )
        for row in file_rows
    ]

    return ConversionJob(
        job_id=job_row["job_id"],
        status=job_row["status"],
        created_at=job_row["created_at"],
        updated_at=job_row["updated_at"],
        total_files=job_row["total_files"],
        processed_files=job_row["processed_files"],
        current_file=job_row["current_file"],
        target_format=job_row["target_format"],
        error=job_row["error"],
        workers=job_row["workers"],
        options_json=job_row["options_json"],
        zip_path=job_row["zip_path"],
        files=files,
    )
