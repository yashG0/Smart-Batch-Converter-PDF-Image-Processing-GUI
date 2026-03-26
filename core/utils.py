from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_OUTPUT_FORMATS = {"png", "jpg", "jpeg", "webp"}


@dataclass(slots=True)
class ConversionResult:
    source: Path
    outputs: list[Path]
    success: bool
    message: str = ""


def ensure_directory(path: Path | str) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def validate_existing_files(paths: Iterable[Path | str]) -> list[Path]:
    resolved: list[Path] = []
    for item in paths:
        candidate = Path(item)
        if not candidate.exists():
            raise FileNotFoundError(f"File not found: {candidate}")
        if not candidate.is_file():
            raise ValueError(f"Path is not a file: {candidate}")
        resolved.append(candidate)
    return resolved


def normalize_output_format(target_format: str) -> str:
    normalized = target_format.lower().strip()
    if normalized not in SUPPORTED_OUTPUT_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
        raise ValueError(f"Unsupported output format: {target_format}. Supported: {supported}")
    return "jpg" if normalized == "jpeg" else normalized


def extension_of(path: Path | str) -> str:
    return Path(path).suffix.lower()


def is_image_file(path: Path | str) -> bool:
    return extension_of(path) in IMAGE_EXTENSIONS


def is_pdf_file(path: Path | str) -> bool:
    return extension_of(path) in PDF_EXTENSIONS


def build_output_path(
    *,
    source_file: Path,
    output_dir: Path | str,
    target_format: str,
    suffix: str | None = None,
) -> Path:
    directory = ensure_directory(output_dir)
    fmt = normalize_output_format(target_format)
    base = source_file.stem
    postfix = f"_{suffix}" if suffix else ""
    return directory / f"{base}{postfix}.{fmt}"
