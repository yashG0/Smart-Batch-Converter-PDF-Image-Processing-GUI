from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from queue import Queue
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from core.processing import ProcessResult, ProcessingOptions, process_files_parallel

JobStatus = str


@dataclass(slots=True)
class ConversionJob:
    job_id: str
    status: JobStatus
    created_at: datetime
    total_files: int
    processed_files: int = 0
    current_file: str = ""
    target_format: str = ""
    results: list[ProcessResult] | None = None
    zip_bytes: bytes = b""
    error: str = ""
    completed_at: datetime | None = None
    workers: int = 1
    options: ProcessingOptions | None = None
    payloads: list[tuple[str, bytes]] | None = None


_jobs: dict[str, ConversionJob] = {}
_jobs_lock = threading.Lock()
_job_queue: Queue[str] = Queue()
_worker_started = False


def _unique_name(file_name: str, seen: dict[str, int]) -> str:
    count = seen.get(file_name, 0)
    seen[file_name] = count + 1
    if count == 0:
        return file_name
    dot = file_name.rfind(".")
    if dot == -1:
        return f"{file_name}_{count}"
    return f"{file_name[:dot]}_{count}{file_name[dot:]}"


def _build_zip(results: list[ProcessResult]) -> bytes:
    buffer = BytesIO()
    seen_names: dict[str, int] = {}
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for result in results:
            if not result.success:
                continue
            for output in result.outputs:
                archive_name = _unique_name(output.filename, seen_names)
                archive.writestr(archive_name, output.content)
    return buffer.getvalue()


def _process_job(job_id: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        payloads = job.payloads or []
        options = job.options
        workers = job.workers
        target_format = job.target_format
        job.status = "processing"

    def on_progress(completed: int, total: int, current_name: str) -> None:
        with _jobs_lock:
            item = _jobs.get(job_id)
            if item is None:
                return
            item.processed_files = completed
            item.total_files = total
            item.current_file = current_name

    try:
        results = process_files_parallel(
            payloads,
            target_format=target_format,
            options=options,
            max_workers=workers,
            use_processes=False,
            progress_callback=on_progress,
        )
        with _jobs_lock:
            item = _jobs.get(job_id)
            if item is None:
                return
            item.results = results
            item.zip_bytes = _build_zip(results)
            item.status = "done"
            item.processed_files = item.total_files
            item.current_file = ""
            item.completed_at = datetime.now(timezone.utc)
            item.payloads = None
    except Exception as exc:
        with _jobs_lock:
            item = _jobs.get(job_id)
            if item is None:
                return
            item.status = "failed"
            item.error = str(exc)
            item.completed_at = datetime.now(timezone.utc)
            item.payloads = None


def _worker_loop() -> None:
    while True:
        job_id = _job_queue.get()
        try:
            _process_job(job_id)
        finally:
            _job_queue.task_done()


def _ensure_worker_started() -> None:
    global _worker_started
    if _worker_started:
        return
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
    now = datetime.now(timezone.utc)
    job = ConversionJob(
        job_id=job_id,
        status="pending",
        created_at=now,
        total_files=len(payloads),
        target_format=target_format,
        workers=max(1, workers),
        options=options,
        payloads=payloads,
    )
    with _jobs_lock:
        _jobs[job_id] = job
    _job_queue.put(job_id)
    return job_id


def get_job(job_id: str) -> ConversionJob | None:
    with _jobs_lock:
        return _jobs.get(job_id)
