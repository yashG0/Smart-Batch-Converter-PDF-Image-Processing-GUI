from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from os import cpu_count

from .engine import process_file
from .models import ProcessResult, ProcessingOptions, ProgressCallback


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
        futures = {executor.submit(_process_single_task, task): (task[0], task[1]) for task in tasks}
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

