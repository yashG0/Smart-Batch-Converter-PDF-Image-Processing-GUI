from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from core.processing import process_file, process_files_parallel
from core.utils import ensure_directory


def create_sample_image(path: Path, label: str, color: str) -> None:
    image = Image.new("RGB", (300, 180), color=color)
    draw = ImageDraw.Draw(image)
    draw.text((16, 16), label, fill="white")
    image.save(path)


def create_sample_pdf(path: Path, label: str) -> None:
    first = Image.new("RGB", (400, 220), color="#457b9d")
    second = Image.new("RGB", (400, 220), color="#1d3557")
    ImageDraw.Draw(first).text((24, 24), f"{label} page 1", fill="white")
    ImageDraw.Draw(second).text((24, 24), f"{label} page 2", fill="white")
    first.save(path, "PDF", save_all=True, append_images=[second])


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    base_dir = Path("output") / "test_processing"
    input_dir = base_dir / "input"

    if base_dir.exists():
        shutil.rmtree(base_dir)
    ensure_directory(input_dir)

    image_path = input_dir / "phase2_image.png"
    pdf_path = input_dir / "phase2_doc.pdf"
    text_path = input_dir / "notes.txt"

    create_sample_image(image_path, "phase2-image", "#2a9d8f")
    create_sample_pdf(pdf_path, "phase2-pdf")
    text_path.write_text("not a supported file type", encoding="utf-8")

    image_bytes = image_path.read_bytes()
    pdf_bytes = pdf_path.read_bytes()
    text_bytes = text_path.read_bytes()

    image_result = process_file("phase2_image.png", image_bytes, "jpg")
    assert_true(image_result.success, "Image processing should succeed.")
    assert_true(image_result.file_type == "image", "Image type detection failed.")
    assert_true(len(image_result.outputs) == 1, "Image should return one output.")

    pdf_result = process_file("phase2_doc.pdf", pdf_bytes, "png")
    assert_true(pdf_result.success, "PDF processing should succeed.")
    assert_true(pdf_result.file_type == "pdf", "PDF type detection failed.")
    assert_true(len(pdf_result.outputs) >= 2, "PDF should return page outputs.")

    empty_result = process_file("empty.png", b"", "png")
    assert_true(not empty_result.success, "Empty file should be rejected.")
    assert_true("Empty file" in empty_result.message, "Empty-file error message is missing.")

    unsupported_result = process_file("notes.txt", text_bytes, "png")
    assert_true(not unsupported_result.success, "Unsupported file should be rejected.")
    assert_true(
        "Unsupported file type" in unsupported_result.message,
        "Unsupported-file error message is missing.",
    )

    corrupted_image_result = process_file("broken.jpg", b"this-is-not-an-image", "png")
    assert_true(not corrupted_image_result.success, "Corrupted image should fail.")

    corrupted_pdf_result = process_file("broken.pdf", b"%PDF-broken-content", "png")
    assert_true(not corrupted_pdf_result.success, "Corrupted PDF should fail.")

    parallel_results = process_files_parallel(
        [
            ("phase2_image.png", image_bytes),
            ("phase2_doc.pdf", pdf_bytes),
            ("notes.txt", text_bytes),
            ("empty.png", b""),
        ],
        target_format="png",
        max_workers=4,
    )
    assert_true(len(parallel_results) == 4, "Parallel processing should return all results.")
    assert_true(parallel_results[0].success, "Parallel image conversion should succeed.")
    assert_true(parallel_results[1].success, "Parallel PDF conversion should succeed.")
    assert_true(not parallel_results[2].success, "Parallel unsupported file should fail.")
    assert_true(not parallel_results[3].success, "Parallel empty file should fail.")

    print("Phase 2 smart processing test passed.")
    print(f"Image outputs from one call: {len(image_result.outputs)}")
    print(f"PDF outputs from one call: {len(pdf_result.outputs)}")
    print(f"Parallel batch results: {len(parallel_results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
