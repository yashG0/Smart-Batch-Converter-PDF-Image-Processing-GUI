from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

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
