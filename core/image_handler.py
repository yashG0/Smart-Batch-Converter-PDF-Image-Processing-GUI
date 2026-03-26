from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image

from core.utils import (
    ConversionResult,
    build_output_path,
    is_image_file,
    normalize_output_format,
    validate_existing_files,
)


def convert_image_file(
    image_path: Path | str,
    target_format: str,
    output_dir: Path | str,
) -> ConversionResult:
    source = Path(image_path)
    normalized_format = normalize_output_format(target_format)

    if not is_image_file(source):
        return ConversionResult(
            source=source,
            outputs=[],
            success=False,
            message=f"Unsupported image file type: {source.suffix}",
        )

    output_path = build_output_path(
        source_file=source,
        output_dir=output_dir,
        target_format=normalized_format,
    )

    try:
        with Image.open(source) as img:
            converted = img.convert("RGB") if normalized_format in {"jpg", "webp"} else img
            save_format = "JPEG" if normalized_format == "jpg" else normalized_format.upper()
            converted.save(output_path, format=save_format)
        return ConversionResult(source=source, outputs=[output_path], success=True)
    except Exception as exc:
        return ConversionResult(
            source=source,
            outputs=[],
            success=False,
            message=str(exc),
        )


def batch_convert_images(
    image_paths: Iterable[Path | str],
    target_format: str,
    output_dir: Path | str,
) -> list[ConversionResult]:
    paths = validate_existing_files(image_paths)
    return [convert_image_file(path, target_format, output_dir) for path in paths]
