from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from services.jobs import create_job, get_job
from services.processing import ProcessingOptions
from services.processing.models import ProcessResult, ProcessedFile


def test_background_job_persistence_and_outputs(isolated_jobs_storage: Path) -> None:
    del isolated_jobs_storage
    image_path = Path("assets/examples/landscape_demo.png")
    pdf_path = Path("assets/examples/sample_document.pdf")

    payloads = [
        (image_path.name, image_path.read_bytes()),
        (pdf_path.name, pdf_path.read_bytes()),
    ]

    job_id = create_job(
        payloads=payloads,
        target_format="png",
        workers=2,
        options=ProcessingOptions(),
    )
    assert job_id

    started = time.time()
    seen_pending_or_processing = False
    while True:
        job = get_job(job_id)
        assert job is not None
        if job.status in {"pending", "processing"}:
            seen_pending_or_processing = True
        if job.status in {"done", "failed"}:
            break
        if time.time() - started > 30:
            raise TimeoutError("Background job did not finish in expected time.")
        time.sleep(0.1)

    assert seen_pending_or_processing or job.status == "done"
    assert job.status == "done"
    assert len(job.files) == 2
    for record in job.files:
        assert record.source_name
        assert record.status in {"done", "failed"}
        for path in record.output_paths:
            assert Path(path).exists()
    assert job.zip_path
    assert Path(job.zip_path).exists()


def test_create_job_fast_path_uses_processing_directly(
    isolated_jobs_storage: Path,
) -> None:
    del isolated_jobs_storage
    from services.jobs import service as job_service

    payloads = [("quick.png", b"fake-bytes")]
    fake_result = [
        ProcessResult(
            source_name="quick.png",
            success=True,
            file_type="image",
            outputs=[ProcessedFile(filename="quick.png", content=b"ok")],
            message="",
        )
    ]

    with patch.object(job_service, "process_files_parallel", return_value=fake_result) as mocked:
        job_id = job_service.create_job(
            payloads=payloads,
            target_format="png",
            workers=2,
            options=ProcessingOptions(),
        )
        assert job_id
        assert mocked.call_count == 1

    job = job_service.get_job(job_id)
    assert job is not None
    assert job.status in {"done", "failed"}
