from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from io import BytesIO
from os import cpu_count
from typing import Callable

from PIL import Image, UnidentifiedImageError
from pdf2image import convert_from_bytes

from core.utils import detect_file_type, normalize_output_format, safe_stem


@dataclass(slots=True)
class ProcessedFile:
    filename: str
    content: bytes


@dataclass(slots=True)
class ProcessResult:
    source_name: str
    success: bool
    file_type: str | None
    outputs: list[ProcessedFile]
    message: str = ""


@dataclass(slots=True)
class ProcessingOptions:
    resize_enabled: bool = False
    resize_width: int | None = None
    resize_height: int | None = None
    keep_aspect_ratio: bool = True
    quality: int = 85
    png_compress_level: int = 6
    png_optimize: bool = True
    webp_lossless: bool = False
    pdf_dpi: int = 200


ProgressCallback = Callable[[int, int, str], None]


def _apply_resize(image: Image.Image, options: ProcessingOptions) -> Image.Image:
    if not options.resize_enabled:
        return image

    width = options.resize_width
    height = options.resize_height
    if not width and not height:
        return image

    original_width, original_height = image.size
    if options.keep_aspect_ratio:
        if width and height:
            resized = image.copy()
            resized.thumbnail((width, height), resample=Image.Resampling.LANCZOS)
            return resized
        if width and not height:
            ratio = width / original_width
            new_size = (width, max(1, int(original_height * ratio)))
            return image.resize(new_size, resample=Image.Resampling.LANCZOS)
        if height and not width:
            ratio = height / original_height
            new_size = (max(1, int(original_width * ratio)), height)
            return image.resize(new_size, resample=Image.Resampling.LANCZOS)
        return image

    if width and height:
        return image.resize((width, height), resample=Image.Resampling.LANCZOS)
    return image


def _save_image_to_bytes(
    image: Image.Image,
    target_format: str,
    options: ProcessingOptions,
) -> bytes:
    buffer = BytesIO()
    save_format = "JPEG" if target_format == "jpg" else target_format.upper()
    resized = _apply_resize(image, options)
    to_save = resized.convert("RGB") if target_format in {"jpg", "webp"} else resized

    save_kwargs: dict[str, int | bool] = {}
    if target_format == "jpg":
        save_kwargs["quality"] = max(1, min(100, options.quality))
        save_kwargs["optimize"] = True
    elif target_format == "webp":
        save_kwargs["quality"] = max(1, min(100, options.quality))
        save_kwargs["lossless"] = options.webp_lossless
    elif target_format == "png":
        save_kwargs["compress_level"] = max(0, min(9, options.png_compress_level))
        save_kwargs["optimize"] = options.png_optimize

    to_save.save(buffer, format=save_format, **save_kwargs)
    return buffer.getvalue()


def process_file(
    name: str,
    content: bytes,
    target_format: str,
    options: ProcessingOptions | None = None,
) -> ProcessResult:
    normalized_format = normalize_output_format(target_format)
    effective_options = options or ProcessingOptions()

    if not content:
        return ProcessResult(
            source_name=name,
            success=False,
            file_type=None,
            outputs=[],
            message="Empty file is not allowed.",
        )

    file_type = detect_file_type(name, content)
    if file_type is None:
        return ProcessResult(
            source_name=name,
            success=False,
            file_type=None,
            outputs=[],
            message="Unsupported file type. Only PDF and common image files are accepted.",
        )

    base = safe_stem(name)

    if file_type == "image":
        try:
            with Image.open(BytesIO(content)) as img:
                output_content = _save_image_to_bytes(img, normalized_format, effective_options)
            return ProcessResult(
                source_name=name,
                success=True,
                file_type="image",
                outputs=[ProcessedFile(filename=f"{base}.{normalized_format}", content=output_content)],
            )
        except UnidentifiedImageError:
            return ProcessResult(
                source_name=name,
                success=False,
                file_type="image",
                outputs=[],
                message="Corrupted or unreadable image file.",
            )
        except Exception as exc:
            return ProcessResult(
                source_name=name,
                success=False,
                file_type="image",
                outputs=[],
                message=str(exc),
            )

    try:
        pages = convert_from_bytes(content, dpi=effective_options.pdf_dpi)
        if not pages:
            return ProcessResult(
                source_name=name,
                success=False,
                file_type="pdf",
                outputs=[],
                message="PDF has no readable pages.",
            )

        outputs: list[ProcessedFile] = []
        for index, page in enumerate(pages, start=1):
            output_content = _save_image_to_bytes(page, normalized_format, effective_options)
            outputs.append(
                ProcessedFile(
                    filename=f"{base}_page_{index}.{normalized_format}",
                    content=output_content,
                )
            )

        return ProcessResult(
            source_name=name,
            success=True,
            file_type="pdf",
            outputs=outputs,
        )
    except Exception:
        return ProcessResult(
            source_name=name,
            success=False,
            file_type="pdf",
            outputs=[],
            message="Corrupted or unreadable PDF file.",
        )


def _process_single_task(
    task: tuple[int, str, bytes, str, ProcessingOptions],
) -> tuple[int, ProcessResult]:
    index, name, content, target_format, options = task
    return index, process_file(
        name=name,
        content=content,
        target_format=target_format,
        options=options,
    )


def process_files_parallel(
    files: list[tuple[str, bytes]],
    target_format: str,
    *,
    options: ProcessingOptions | None = None,
    max_workers: int | None = None,
    use_processes: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> list[ProcessResult]:
    if not files:
        return []

    effective_options = options or ProcessingOptions()
    total = len(files)
    resolved_workers = max_workers if max_workers and max_workers > 0 else min(32, total)
    if resolved_workers <= 1:
        results: list[ProcessResult] = []
        for index, (name, content) in enumerate(files, start=1):
            result = process_file(
                name=name,
                content=content,
                target_format=target_format,
                options=effective_options,
            )
            results.append(result)
            if progress_callback is not None:
                progress_callback(index, total, name)
        return results

    tasks = [
        (index, name, content, target_format, effective_options)
        for index, (name, content) in enumerate(files)
    ]
    ordered_results: list[ProcessResult | None] = [None] * total

    if use_processes:
        default_workers = max(1, (cpu_count() or 2) - 1)
        resolved_workers = min(resolved_workers, default_workers)
        executor_cls = ProcessPoolExecutor
    else:
        executor_cls = ThreadPoolExecutor

    with executor_cls(max_workers=resolved_workers) as executor:
        futures = {
            executor.submit(_process_single_task, task): (task[0], task[1]) for task in tasks
        }
        completed = 0
        for future in as_completed(futures):
            fallback_index, fallback_name = futures[future]
            try:
                index, result = future.result()
            except Exception as exc:
                index = fallback_index
                result = ProcessResult(
                    source_name=fallback_name,
                    success=False,
                    file_type=None,
                    outputs=[],
                    message=f"Unexpected processing error: {exc}",
                )
            ordered_results[index] = result
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, total, result.source_name)

    return [item for item in ordered_results if item is not None]
