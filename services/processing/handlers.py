from __future__ import annotations

from io import BytesIO

import fitz
import img2pdf
from PIL import Image, UnidentifiedImageError

from core.utils import safe_stem

from .models import ProcessResult, ProcessedFile, ProcessingOptions


def _apply_resize(image: Image.Image, options: ProcessingOptions) -> Image.Image:
    if not options.resize_enabled:
        return image

    width = options.resize_width
    height = options.resize_height
    if not width and not height:
        return image

    original_width, original_height = image.size
    if options.keep_aspect_ratio:
        if width and height:
            resized = image.copy()
            resized.thumbnail((width, height), resample=Image.Resampling.LANCZOS)
            return resized
        if width and not height:
            ratio = width / original_width
            new_size = (width, max(1, int(original_height * ratio)))
            return image.resize(new_size, resample=Image.Resampling.LANCZOS)
        if height and not width:
            ratio = height / original_height
            new_size = (max(1, int(original_width * ratio)), height)
            return image.resize(new_size, resample=Image.Resampling.LANCZOS)
        return image

    if width and height:
        return image.resize((width, height), resample=Image.Resampling.LANCZOS)
    return image


def save_image_to_bytes(image: Image.Image, target_format: str, options: ProcessingOptions) -> bytes:
    buffer = BytesIO()
    save_format = "JPEG" if target_format == "jpg" else target_format.upper()
    resized = _apply_resize(image, options)
    to_save = resized.convert("RGB") if target_format in {"jpg", "webp"} else resized

    save_kwargs: dict[str, int | bool] = {}
    if target_format == "jpg":
        save_kwargs["quality"] = max(1, min(100, options.quality))
        save_kwargs["optimize"] = True
    elif target_format == "webp":
        save_kwargs["quality"] = max(1, min(100, options.quality))
        save_kwargs["lossless"] = options.webp_lossless
    elif target_format == "png":
        save_kwargs["compress_level"] = max(0, min(9, options.png_compress_level))
        save_kwargs["optimize"] = options.png_optimize

    to_save.save(buffer, format=save_format, **save_kwargs)
    return buffer.getvalue()


def _convert_image_to_pdf(content: bytes, options: ProcessingOptions) -> bytes:
    with Image.open(BytesIO(content)) as img:
        source_format = (img.format or "").upper()
        if not options.resize_enabled and source_format in {"JPEG", "JPG", "PNG", "TIFF"}:
            return img2pdf.convert(content)

        processed = _apply_resize(img, options)
        # img2pdf expects an image file payload; encode to PNG for broad compatibility.
        buffer = BytesIO()
        processed.save(buffer, format="PNG")
    return img2pdf.convert(buffer.getvalue())


def handle_image(name: str, content: bytes, target_format: str, options: ProcessingOptions) -> ProcessResult:
    base = safe_stem(name)
    try:
        if target_format == "pdf":
            output_content = _convert_image_to_pdf(content, options)
        else:
            with Image.open(BytesIO(content)) as img:
                output_content = save_image_to_bytes(img, target_format, options)
        return ProcessResult(
            source_name=name,
            success=True,
            file_type="image",
            outputs=[ProcessedFile(filename=f"{base}.{target_format}", content=output_content)],
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


def handle_pdf(name: str, content: bytes, target_format: str, options: ProcessingOptions) -> ProcessResult:
    base = safe_stem(name)
    if target_format == "pdf":
        return ProcessResult(
            source_name=name,
            success=False,
            file_type="pdf",
            outputs=[],
            message="PDF to PDF conversion is not supported.",
        )
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            if document.page_count == 0:
                return ProcessResult(
                    source_name=name,
                    success=False,
                    file_type="pdf",
                    outputs=[],
                    message="PDF has no readable pages.",
                )

            scale = max(0.1, options.pdf_dpi / 72.0)
            matrix = fitz.Matrix(scale, scale)
            outputs: list[ProcessedFile] = []
            for index in range(document.page_count):
                page = document[index]
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes(
                    "RGB",
                    (pixmap.width, pixmap.height),
                    pixmap.samples,
                )
                output_content = save_image_to_bytes(image, target_format, options)
                outputs.append(
                    ProcessedFile(
                        filename=f"{base}_page_{index + 1}.{target_format}",
                        content=output_content,
                    )
                )

        if not outputs:
            return ProcessResult(
                source_name=name,
                success=False,
                file_type="pdf",
                outputs=[],
                message="PDF has no readable pages.",
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
