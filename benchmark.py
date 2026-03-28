from __future__ import annotations

from io import BytesIO
from statistics import mean
from time import perf_counter

from PIL import Image, ImageDraw

from services.processing import ProcessingOptions, process_file, process_files_parallel


def create_sample_image_bytes(size: tuple[int, int] = (2400, 1600)) -> bytes:
    image = Image.new("RGB", size, "#1d3557")
    drawer = ImageDraw.Draw(image)
    drawer.text((40, 40), "benchmark-image", fill="white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def create_sample_pdf_bytes(pages: int = 3, size: tuple[int, int] = (1600, 1000)) -> bytes:
    page_list: list[Image.Image] = []
    for index in range(pages):
        page = Image.new("RGB", size, "#0b132b" if index % 2 == 0 else "#1c2541")
        drawer = ImageDraw.Draw(page)
        drawer.text((40, 40), f"benchmark-pdf page {index + 1}", fill="white")
        page_list.append(page)

    buffer = BytesIO()
    first, rest = page_list[0], page_list[1:]
    first.save(buffer, format="PDF", save_all=True, append_images=rest)
    for page in page_list:
        page.close()
    return buffer.getvalue()


def legacy_image_to_pdf_pillow(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as img:
        converted = img.convert("RGB")
        buffer = BytesIO()
        converted.save(buffer, format="PDF")
    return buffer.getvalue()


def current_image_to_pdf(image_bytes: bytes) -> bytes:
    result = process_file(
        name="sample.jpg",
        content=image_bytes,
        target_format="pdf",
        options=ProcessingOptions(),
    )
    if not result.success:
        raise RuntimeError(result.message)
    return result.outputs[0].content


def current_pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    result = process_file(
        name="sample.pdf",
        content=pdf_bytes,
        target_format="png",
        options=ProcessingOptions(pdf_dpi=144),
    )
    if not result.success:
        raise RuntimeError(result.message)
    return [item.content for item in result.outputs]


def optional_legacy_pdf_to_images(pdf_bytes: bytes) -> list[bytes] | None:
    try:
        from pdf2image import convert_from_bytes  # type: ignore
    except Exception:
        return None

    pages = convert_from_bytes(pdf_bytes, dpi=144)
    outputs: list[bytes] = []
    for page in pages:
        buffer = BytesIO()
        page.save(buffer, format="PNG")
        outputs.append(buffer.getvalue())
    return outputs


def run_benchmark(label: str, func, payload: bytes, runs: int = 5) -> tuple[float, int]:
    # Warmup run so import/initialization is not counted.
    warmup_output = func(payload)
    output_size = sum(len(item) for item in warmup_output) if isinstance(warmup_output, list) else len(warmup_output)

    timings: list[float] = []
    for _ in range(runs):
        start = perf_counter()
        func(payload)
        timings.append(perf_counter() - start)
    avg_time = mean(timings)
    print(f"{label:<34} avg={avg_time:.4f}s  output={output_size/1024:.1f}KB")
    return avg_time, output_size


def run_batch_benchmark(label: str, func, payloads: list[tuple[str, bytes]], runs: int = 3) -> float:
    # Warmup run so startup cost (imports, caches) is less noisy.
    func(payloads)

    timings: list[float] = []
    for _ in range(runs):
        start = perf_counter()
        func(payloads)
        timings.append(perf_counter() - start)
    avg_time = mean(timings)
    print(f"{label:<34} avg={avg_time:.4f}s")
    return avg_time


def print_gain(new_time: float, old_time: float, label: str) -> None:
    if old_time <= 0:
        return
    improvement = ((old_time - new_time) / old_time) * 100
    speedup = old_time / new_time if new_time > 0 else 0.0
    print(f"{label}: {improvement:.1f}% faster ({speedup:.2f}x)")


def _threaded_batch_convert(payloads: list[tuple[str, bytes]]) -> None:
    process_files_parallel(
        payloads,
        target_format="png",
        options=ProcessingOptions(pdf_dpi=144),
        max_workers=4,
        use_processes=False,
    )


def _process_batch_convert(payloads: list[tuple[str, bytes]]) -> None:
    process_files_parallel(
        payloads,
        target_format="png",
        options=ProcessingOptions(pdf_dpi=144),
        max_workers=4,
        use_processes=True,
    )


def main() -> None:
    print("Benchmarking conversion pipeline on this machine...\n")

    image_bytes = create_sample_image_bytes()
    pdf_bytes = create_sample_pdf_bytes()

    print("Image -> PDF")
    legacy_img_time, _ = run_benchmark("Legacy (Pillow PDF save)", legacy_image_to_pdf_pillow, image_bytes)
    current_img_time, _ = run_benchmark("Current (img2pdf)", current_image_to_pdf, image_bytes)
    print_gain(current_img_time, legacy_img_time, "Image->PDF gain")
    print()

    print("PDF -> Image")
    current_pdf_time, _ = run_benchmark("Current (PyMuPDF)", current_pdf_to_images, pdf_bytes)
    legacy_pdf_outputs = optional_legacy_pdf_to_images(pdf_bytes)
    if legacy_pdf_outputs is None:
        print("Legacy (pdf2image)               skipped (pdf2image not installed)")
    else:
        legacy_pdf_time, _ = run_benchmark(
            "Legacy (pdf2image)",
            lambda payload: optional_legacy_pdf_to_images(payload) or [],
            pdf_bytes,
        )
        print_gain(current_pdf_time, legacy_pdf_time, "PDF->Image gain")

    print()
    print("Batch Parallel (job-style workload)")
    batch_payloads: list[tuple[str, bytes]] = []
    for index in range(6):
        batch_payloads.append((f"bench_{index + 1}.pdf", pdf_bytes))
    thread_batch_time = run_batch_benchmark("ThreadPoolExecutor", _threaded_batch_convert, batch_payloads)
    process_batch_time = run_batch_benchmark("ProcessPoolExecutor", _process_batch_convert, batch_payloads)
    print_gain(process_batch_time, thread_batch_time, "Batch processes vs threads")

    print("\nTip: run on your real files for more representative numbers.")


if __name__ == "__main__":
    main()
