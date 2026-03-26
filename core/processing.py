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


ProgressCallback = Callable[[int, int, str], None]


def _save_image_to_bytes(image: Image.Image, target_format: str) -> bytes:
    buffer = BytesIO()
    save_format = "JPEG" if target_format == "jpg" else target_format.upper()
    to_save = image.convert("RGB") if target_format in {"jpg", "webp"} else image
    to_save.save(buffer, format=save_format)
    return buffer.getvalue()


def process_file(name: str, content: bytes, target_format: str) -> ProcessResult:
    normalized_format = normalize_output_format(target_format)

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
                output_content = _save_image_to_bytes(img, normalized_format)
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
        pages = convert_from_bytes(content, dpi=200)
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
            output_content = _save_image_to_bytes(page, normalized_format)
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


def _process_single_task(task: tuple[int, str, bytes, str]) -> tuple[int, ProcessResult]:
    index, name, content, target_format = task
    return index, process_file(name=name, content=content, target_format=target_format)


def process_files_parallel(
    files: list[tuple[str, bytes]],
    target_format: str,
    *,
    max_workers: int | None = None,
    use_processes: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> list[ProcessResult]:
    if not files:
        return []

    total = len(files)
    resolved_workers = max_workers if max_workers and max_workers > 0 else min(32, total)
    if resolved_workers <= 1:
        results: list[ProcessResult] = []
        for index, (name, content) in enumerate(files, start=1):
            result = process_file(name=name, content=content, target_format=target_format)
            results.append(result)
            if progress_callback is not None:
                progress_callback(index, total, name)
        return results

    tasks = [
        (index, name, content, target_format)
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
        futures = [executor.submit(_process_single_task, task) for task in tasks]
        completed = 0
        for future in as_completed(futures):
            index, result = future.result()
            ordered_results[index] = result
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, total, result.source_name)

    return [item for item in ordered_results if item is not None]
