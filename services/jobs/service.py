from __future__ import annotations

from uuid import uuid4

from services.processing import ProcessingOptions

from .models import ConversionJob, QueuedJob
from .storage import fetch_job, insert_pending_job
from .worker import enqueue_job


def create_job(
    payloads: list[tuple[str, bytes]],
    target_format: str,
    workers: int,
    options: ProcessingOptions,
) -> str:
    job_id = uuid4().hex[:12]
    normalized_workers = max(1, workers)
    insert_pending_job(
        job_id=job_id,
        payloads=payloads,
        target_format=target_format,
        workers=normalized_workers,
        options=options,
    )
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

