from __future__ import annotations

import time
from pathlib import Path

from core.job_manager import create_job, get_job
from core.processing import ProcessingOptions


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
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
    assert_true(bool(job_id), "Job ID should be generated.")

    started = time.time()
    seen_pending_or_processing = False
    while True:
        job = get_job(job_id)
        assert_true(job is not None, "Job should exist.")
        if job.status in {"pending", "processing"}:
            seen_pending_or_processing = True
        if job.status in {"done", "failed"}:
            break
        if time.time() - started > 30:
            raise TimeoutError("Background job did not finish in expected time.")
        time.sleep(0.1)

    # Fast-path jobs may complete before first poll, so allow direct done state.
    assert_true(
        seen_pending_or_processing or job.status == "done",
        "Job should either pass through pending/processing or complete immediately via fast-path.",
    )
    assert_true(job.status == "done", f"Expected job to finish as done, got: {job.status}")
    assert_true(len(job.files) == 2, "Expected 2 file records.")
    for record in job.files:
        assert_true(bool(record.source_name), "Source filename should be persisted.")
        assert_true(record.status in {"done", "failed"}, "File status should be persisted.")
        for path in record.output_paths:
            assert_true(Path(path).exists(), "Output path should exist on disk.")
    assert_true(bool(job.zip_path), "ZIP path should be persisted.")
    assert_true(Path(job.zip_path).exists(), "ZIP file should exist on disk.")

    print(f"Background job test passed. job_id={job_id}, status={job.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
