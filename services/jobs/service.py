from __future__ import annotations

from uuid import uuid4

from services.common.logging import get_logger
from services.processing import ProcessingOptions, process_files_parallel

from .models import ConversionJob, QueuedJob
from .storage import (
    fetch_job,
    insert_pending_job,
    mark_job_done,
    mark_job_failed,
    update_job_progress,
)
from .worker import enqueue_job

FAST_PATH_MAX_FILES = 3
FAST_PATH_MAX_TOTAL_BYTES = 24 * 1024 * 1024


def _should_use_fast_path(payloads: list[tuple[str, bytes]]) -> bool:
    if len(payloads) > FAST_PATH_MAX_FILES:
        return False
    total_bytes = sum(len(content) for _, content in payloads)
    return total_bytes <= FAST_PATH_MAX_TOTAL_BYTES


def _should_use_process_pool(payloads: list[tuple[str, bytes]], workers: int) -> bool:
    if workers <= 1 or len(payloads) <= 1:
        return False
    # PDF rendering and large-image conversion are CPU-heavy; prefer processes here.
    return any(name.lower().endswith(".pdf") for name, _ in payloads)


def create_job(
    payloads: list[tuple[str, bytes]],
    target_format: str,
    workers: int,
    options: ProcessingOptions,
) -> str:
    job_id = uuid4().hex[:12]
    correlation_id = uuid4().hex[:8]
    logger = get_logger("jobs.service", job_id=job_id, correlation_id=correlation_id)
    normalized_workers = max(1, workers)
    logger.info(
        "create_job requested",
    )
    insert_pending_job(
        job_id=job_id,
        payloads=payloads,
        target_format=target_format,
        workers=normalized_workers,
        options=options,
    )

    if _should_use_fast_path(payloads):
        logger.info("using fast-path execution")
        try:
            update_job_progress(job_id, processed=0, total=len(payloads), current_file="")

            def on_progress(completed: int, total: int, current_name: str) -> None:
                update_job_progress(
                    job_id,
                    processed=completed,
                    total=total,
                    current_file=current_name,
                )

            results = process_files_parallel(
                payloads,
                target_format=target_format,
                options=options,
                max_workers=min(2, normalized_workers),
                use_processes=_should_use_process_pool(payloads, normalized_workers),
                progress_callback=on_progress,
            )
            mark_job_done(job_id, results=results, target_format=target_format)
            logger.info("fast-path execution completed")
        except Exception as exc:
            mark_job_failed(job_id, str(exc))
            logger.exception("fast-path execution failed: %s", exc)
    else:
        logger.info("enqueuing background job")
        enqueue_job(
            QueuedJob(
                job_id=job_id,
                payloads=payloads,
                target_format=target_format,
                workers=normalized_workers,
                options=options,
            )
        )

    return job_id


def get_job(job_id: str) -> ConversionJob | None:
    return fetch_job(job_id)
