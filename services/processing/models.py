from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


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
ConversionHandler = Callable[[str, bytes, str, ProcessingOptions], ProcessResult]
HandlerRegistry = dict[str, ConversionHandler]

