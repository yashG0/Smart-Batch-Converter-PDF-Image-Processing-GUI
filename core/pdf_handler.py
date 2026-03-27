from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.utils import ConversionResult, ensure_directory, validate_existing_files
from services.processing import ProcessingOptions, process_file


def _write_outputs(output_dir: Path, outputs) -> list[Path]:
    written_paths: list[Path] = []
    for item in outputs:
        target = output_dir / item.filename
        base = target.stem
        ext = target.suffix
        suffix = 1
        while target.exists():
            target = output_dir / f"{base}_{suffix}{ext}"
            suffix += 1
        target.write_bytes(item.content)
        written_paths.append(target)
    return written_paths


def convert_pdf_file(
    pdf_path: Path | str,
    target_format: str,
    output_dir: Path | str,
    dpi: int = 200,
) -> ConversionResult:
    source = Path(pdf_path)
    destination = ensure_directory(output_dir)
    result = process_file(
        name=source.name,
        content=source.read_bytes(),
        target_format=target_format,
        options=ProcessingOptions(pdf_dpi=dpi),
    )
    if not result.success:
        return ConversionResult(
            source=source,
            outputs=[],
            success=False,
            message=result.message,
        )

    outputs = _write_outputs(destination, result.outputs)
    return ConversionResult(source=source, outputs=outputs, success=True)


def batch_convert_pdfs(
    pdf_paths: Iterable[Path | str],
    target_format: str,
    output_dir: Path | str,
    dpi: int = 200,
) -> list[ConversionResult]:
    paths = validate_existing_files(pdf_paths)
    return [convert_pdf_file(path, target_format, output_dir, dpi=dpi) for path in paths]

