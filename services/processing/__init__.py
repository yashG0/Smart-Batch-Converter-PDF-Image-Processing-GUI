from .engine import process_file
from .handlers import handle_image, handle_pdf
from .models import (
    ConversionHandler,
    HandlerRegistry,
    ProcessResult,
    ProcessedFile,
    ProcessingOptions,
    ProgressCallback,
)
from .parallel import process_files_parallel
from .registry import get_registered_handlers, register_handler, resolve_file_type

# Register built-ins once at import time.
register_handler("pdf", handle_pdf, extensions=(".pdf",))
register_handler(
    "image",
    handle_image,
    extensions=(".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"),
)

__all__ = [
    "ConversionHandler",
    "HandlerRegistry",
    "ProcessResult",
    "ProcessedFile",
    "ProcessingOptions",
    "ProgressCallback",
    "get_registered_handlers",
    "handle_image",
    "handle_pdf",
    "process_file",
    "process_files_parallel",
    "register_handler",
    "resolve_file_type",
]
