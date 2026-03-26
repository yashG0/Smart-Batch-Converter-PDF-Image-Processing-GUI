from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pdf2image import convert_from_path

from core.utils import (
    ConversionResult,
    build_output_path,
    is_pdf_file,
    normalize_output_format,
    validate_existing_files,
)


def convert_pdf_file(
    pdf_path: Path | str,
    target_format: str,
    output_dir: Path | str,
    dpi: int = 200,
) -> ConversionResult:
    source = Path(pdf_path)
    normalized_format = normalize_output_format(target_format)

    if not is_pdf_file(source):
        return ConversionResult(
            source=source,
            outputs=[],
            success=False,
            message=f"Unsupported PDF file type: {source.suffix}",
        )

    try:
        pages = convert_from_path(str(source), dpi=dpi)
    except Exception as exc:
        return ConversionResult(source=source, outputs=[], success=False, message=str(exc))

    outputs: list[Path] = []
    try:
        for page_index, page_image in enumerate(pages, start=1):
            output_path = build_output_path(
                source_file=source,
                output_dir=output_dir,
                target_format=normalized_format,
                suffix=f"page_{page_index}",
            )
            save_format = "JPEG" if normalized_format == "jpg" else normalized_format.upper()
            image_to_save = (
                page_image.convert("RGB")
                if normalized_format in {"jpg", "webp"}
                else page_image
            )
            image_to_save.save(output_path, format=save_format)
            outputs.append(output_path)
    except Exception as exc:
        return ConversionResult(source=source, outputs=outputs, success=False, message=str(exc))

    return ConversionResult(source=source, outputs=outputs, success=True)


def batch_convert_pdfs(
    pdf_paths: Iterable[Path | str],
    target_format: str,
    output_dir: Path | str,
    dpi: int = 200,
) -> list[ConversionResult]:
    paths = validate_existing_files(pdf_paths)
    return [convert_pdf_file(path, target_format, output_dir, dpi=dpi) for path in paths]
