from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from services.processing import (
    ProcessResult,
    ProcessedFile,
    ProcessingOptions,
    process_file,
    process_files_parallel,
    register_handler,
)

from conftest import create_sample_image, create_sample_pdf


def _dummy_handler(
    name: str,
    content: bytes,
    target_format: str,
    options: ProcessingOptions,
) -> ProcessResult:
    del options
    payload = f"dummy:{name}:{target_format}:{len(content)}".encode("utf-8")
    return ProcessResult(
        source_name=name,
        success=True,
        file_type="dummy",
        outputs=[ProcessedFile(filename="dummy.txt", content=payload)],
    )


@pytest.mark.parametrize(
    ("target_format", "expected_suffix"),
    [
        ("png", ".png"),
        ("jpg", ".jpg"),
        ("webp", ".webp"),
        ("pdf", ".pdf"),
    ],
)
def test_image_conversion_formats(
    sample_image_bytes: bytes,
    target_format: str,
    expected_suffix: str,
) -> None:
    result = process_file("sample_image.png", sample_image_bytes, target_format)
    assert result.success
    assert result.file_type == "image"
    assert len(result.outputs) == 1
    assert result.outputs[0].filename.endswith(expected_suffix)


def test_processing_failure_cases(
    sample_pdf_bytes: bytes,
    unsupported_file_bytes: bytes,
    corrupted_image_bytes: bytes,
    corrupted_pdf_bytes: bytes,
) -> None:
    empty_result = process_file("empty.png", b"", "png")
    assert not empty_result.success
    assert "Empty file" in empty_result.message

    unsupported_result = process_file("notes.txt", unsupported_file_bytes, "png")
    assert not unsupported_result.success
    assert "Unsupported file type" in unsupported_result.message

    corrupted_image_result = process_file("broken.jpg", corrupted_image_bytes, "png")
    assert not corrupted_image_result.success

    corrupted_pdf_result = process_file("broken.pdf", corrupted_pdf_bytes, "png")
    assert not corrupted_pdf_result.success

    pdf_to_pdf_result = process_file("phase2_doc.pdf", sample_pdf_bytes, "pdf")
    assert not pdf_to_pdf_result.success


def test_invalid_target_format_raises(sample_image_bytes: bytes) -> None:
    with pytest.raises(ValueError):
        process_file("sample_image.png", sample_image_bytes, "gif")


def test_process_file_resize_plugin_and_parallel(sample_input_dir: Path) -> None:
    image_path = sample_input_dir / "phase2_image.png"
    pdf_path = sample_input_dir / "phase2_doc.pdf"
    text_path = sample_input_dir / "notes.txt"

    create_sample_image(image_path, "phase2-image", "#2a9d8f", size=(300, 180))
    create_sample_pdf(pdf_path, "phase2-pdf")
    text_path.write_text("not a supported file type", encoding="utf-8")

    image_bytes = image_path.read_bytes()
    pdf_bytes = pdf_path.read_bytes()
    text_bytes = text_path.read_bytes()

    image_result = process_file("phase2_image.png", image_bytes, "jpg")
    assert image_result.success
    assert image_result.file_type == "image"
    assert len(image_result.outputs) == 1

    pdf_result = process_file("phase2_doc.pdf", pdf_bytes, "png")
    assert pdf_result.success
    assert pdf_result.file_type == "pdf"
    assert len(pdf_result.outputs) >= 2

    resized_result = process_file(
        "phase2_image.png",
        image_bytes,
        "jpg",
        options=ProcessingOptions(
            resize_enabled=True,
            resize_width=100,
            resize_height=100,
            keep_aspect_ratio=False,
            quality=55,
        ),
    )
    assert resized_result.success
    with Image.open(BytesIO(resized_result.outputs[0].content)) as resized_image:
        assert resized_image.size == (100, 100)

    register_handler("dummy", _dummy_handler, extensions=(".dummy",))
    plugin_result = process_file("custom_payload.dummy", b"abc123", "png")
    assert plugin_result.success
    assert plugin_result.file_type == "dummy"
    assert len(plugin_result.outputs) == 1

    parallel_results = process_files_parallel(
        [
            ("phase2_image.png", image_bytes),
            ("phase2_doc.pdf", pdf_bytes),
            ("notes.txt", text_bytes),
            ("empty.png", b""),
        ],
        target_format="png",
        options=ProcessingOptions(
            png_compress_level=9,
            png_optimize=True,
            pdf_dpi=180,
        ),
        max_workers=4,
    )
    assert len(parallel_results) == 4
    assert parallel_results[0].success
    assert parallel_results[1].success
    assert not parallel_results[2].success
    assert not parallel_results[3].success
