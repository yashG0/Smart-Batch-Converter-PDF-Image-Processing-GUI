from __future__ import annotations

from pathlib import Path

from core.image_handler import batch_convert_images
from core.pdf_handler import batch_convert_pdfs

from conftest import create_sample_image, create_sample_pdf


def test_batch_core_conversion(sample_input_dir: Path, tmp_path: Path) -> None:
    image_output_dir = tmp_path / "images_converted"
    pdf_output_dir = tmp_path / "pdfs_converted"
    image_output_dir.mkdir(parents=True, exist_ok=True)
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    image_1 = sample_input_dir / "sample_a.png"
    image_2 = sample_input_dir / "sample_b.jpg"
    pdf_1 = sample_input_dir / "doc_a.pdf"
    pdf_2 = sample_input_dir / "doc_b.pdf"

    create_sample_image(image_1, "sample a", "#219ebc")
    create_sample_image(image_2, "sample b", "#fb8500")
    create_sample_pdf(pdf_1, "doc a")
    create_sample_pdf(pdf_2, "doc b")

    image_results = batch_convert_images(
        [image_1, image_2],
        target_format="webp",
        output_dir=image_output_dir,
    )
    pdf_results = batch_convert_pdfs(
        [pdf_1, pdf_2],
        target_format="png",
        output_dir=pdf_output_dir,
    )

    assert all(item.success for item in image_results)
    assert all(item.success for item in pdf_results)

    generated_image_files = sorted(image_output_dir.glob("*"))
    generated_pdf_files = sorted(pdf_output_dir.glob("*"))

    assert len(generated_image_files) == 2
    assert len(generated_pdf_files) >= 4
