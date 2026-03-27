from __future__ import annotations

from dataclasses import dataclass

from services.processing import ProcessingOptions

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
class QueuedJob:
    job_id: str
    payloads: list[tuple[str, bytes]]
    target_format: str
    workers: int
    options: ProcessingOptions

