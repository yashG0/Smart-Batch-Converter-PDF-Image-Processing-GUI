from __future__ import annotations

from pathlib import Path

from core.utils import detect_file_type

from .models import ConversionHandler, HandlerRegistry

_HANDLERS: HandlerRegistry = {}
_EXTENSION_FILE_TYPE_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tiff": "image",
}


def register_handler(file_type: str, handler: ConversionHandler, extensions: tuple[str, ...] = ()) -> None:
    normalized_type = file_type.strip().lower()
    if not normalized_type:
        raise ValueError("file_type must not be empty.")
    _HANDLERS[normalized_type] = handler

    for ext in extensions:
        normalized_ext = ext.lower()
        if not normalized_ext.startswith("."):
            normalized_ext = f".{normalized_ext}"
        _EXTENSION_FILE_TYPE_MAP[normalized_ext] = normalized_type


def get_registered_handlers() -> HandlerRegistry:
    return dict(_HANDLERS)


def get_handler(file_type: str) -> ConversionHandler | None:
    return _HANDLERS.get(file_type)


def resolve_file_type(name: str, content: bytes) -> str | None:
    detected = detect_file_type(name, content)
    if detected is not None:
        return detected
    extension = Path(name).suffix.lower()
    return _EXTENSION_FILE_TYPE_MAP.get(extension)

