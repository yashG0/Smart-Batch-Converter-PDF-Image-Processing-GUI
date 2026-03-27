from __future__ import annotations

from core.utils import normalize_output_format

from .models import ProcessResult, ProcessingOptions
from .registry import get_handler, resolve_file_type


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

    file_type = resolve_file_type(name, content)
    if file_type is None:
        return ProcessResult(
            source_name=name,
            success=False,
            file_type=None,
            outputs=[],
            message="Unsupported file type. Only PDF and common image files are accepted.",
        )

    handler = get_handler(file_type)
    if handler is None:
        return ProcessResult(
            source_name=name,
            success=False,
            file_type=file_type,
            outputs=[],
            message=f"No registered handler for file type: {file_type}",
        )
    return handler(name, content, normalized_format, effective_options)

