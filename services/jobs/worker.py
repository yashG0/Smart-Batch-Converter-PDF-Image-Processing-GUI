from __future__ import annotations

import threading
from queue import Queue

from services.processing import process_files_parallel

from .models import QueuedJob
from .storage import init_db, mark_job_done, mark_job_failed, update_job_progress

_job_queue: Queue[QueuedJob] = Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _process_job(job: QueuedJob) -> None:
    update_job_progress(job.job_id, processed=0, total=len(job.payloads), current_file="")

    def on_progress(completed: int, total: int, current_name: str) -> None:
        update_job_progress(
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
        mark_job_done(job.job_id, results=results, target_format=job.target_format)
    except Exception as exc:
        mark_job_failed(job.job_id, str(exc))


def _worker_loop() -> None:
    while True:
        job = _job_queue.get()
        try:
            _process_job(job)
        finally:
            _job_queue.task_done()


def ensure_worker_started() -> None:
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        init_db()
        worker = threading.Thread(target=_worker_loop, daemon=True, name="conversion-job-worker")
        worker.start()
        _worker_started = True


def enqueue_job(job: QueuedJob) -> None:
    ensure_worker_started()
    _job_queue.put(job)

