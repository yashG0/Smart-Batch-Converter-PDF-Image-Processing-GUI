from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from core.image_handler import batch_convert_images
from core.pdf_handler import batch_convert_pdfs
from core.utils import ensure_directory


def create_sample_image(path: Path, label: str, color: str) -> None:
    image = Image.new("RGB", (320, 180), color=color)
    drawer = ImageDraw.Draw(image)
    drawer.text((16, 16), label, fill="white")
    image.save(path)


def create_sample_pdf(path: Path, label: str) -> None:
    first = Image.new("RGB", (420, 240), color="#003049")
    second = Image.new("RGB", (420, 240), color="#d62828")
    ImageDraw.Draw(first).text((24, 24), f"{label} - page 1", fill="white")
    ImageDraw.Draw(second).text((24, 24), f"{label} - page 2", fill="white")
    first.save(path, "PDF", save_all=True, append_images=[second])


def summarize_results(kind: str, results: list) -> tuple[int, int]:
    success_count = sum(1 for item in results if item.success)
    fail_count = len(results) - success_count
    print(f"{kind}: {success_count} success, {fail_count} failed")
    for item in results:
        status = "OK" if item.success else "FAIL"
        print(f"  [{status}] {item.source} -> {len(item.outputs)} output(s)")
        if item.message:
            print(f"       reason: {item.message}")
    return success_count, fail_count


def main() -> int:
    base_dir = Path("output") / "test_core"
    input_dir = base_dir / "input"
    image_output_dir = base_dir / "images_converted"
    pdf_output_dir = base_dir / "pdfs_converted"

    if base_dir.exists():
        shutil.rmtree(base_dir)

    ensure_directory(input_dir)
    ensure_directory(image_output_dir)
    ensure_directory(pdf_output_dir)

    image_1 = input_dir / "sample_a.png"
    image_2 = input_dir / "sample_b.jpg"
    pdf_1 = input_dir / "doc_a.pdf"
    pdf_2 = input_dir / "doc_b.pdf"

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

    image_success, image_fail = summarize_results("Image conversions", image_results)
    pdf_success, pdf_fail = summarize_results("PDF conversions", pdf_results)

    generated_image_files = sorted(image_output_dir.glob("*"))
    generated_pdf_files = sorted(pdf_output_dir.glob("*"))

    print(f"Generated image outputs: {len(generated_image_files)}")
    print(f"Generated PDF outputs: {len(generated_pdf_files)}")

    if image_fail > 0 or pdf_fail > 0:
        print("Core test failed: at least one conversion failed.")
        return 1

    if image_success != 2 or len(generated_image_files) != 2:
        print("Core test failed: unexpected image conversion count.")
        return 1

    if pdf_success != 2 or len(generated_pdf_files) < 4:
        print("Core test failed: unexpected PDF conversion count.")
        return 1

    print("Core test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
