from __future__ import annotations

from io import BytesIO
from os import cpu_count
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from core.processing import ProcessResult, ProcessingOptions, process_files_parallel

SUPPORTED_FORMATS = ("png", "jpg", "webp")


def _unique_name(file_name: str, seen: dict[str, int]) -> str:
    count = seen.get(file_name, 0)
    seen[file_name] = count + 1
    if count == 0:
        return file_name

    dot = file_name.rfind(".")
    if dot == -1:
        return f"{file_name}_{count}"
    return f"{file_name[:dot]}_{count}{file_name[dot:]}"


def _build_zip(results: list[ProcessResult]) -> bytes:
    buffer = BytesIO()
    seen_names: dict[str, int] = {}
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for result in results:
            if not result.success:
                continue
            for output in result.outputs:
                archive_name = _unique_name(output.filename, seen_names)
                archive.writestr(archive_name, output.content)
    return buffer.getvalue()


def _convert_uploaded_files(
    files,
    target_format: str,
    workers: int,
    options: ProcessingOptions,
) -> list[ProcessResult]:
    total = len(files)
    progress = st.progress(0, text="Starting conversion...")
    status_box = st.empty()
    payloads = [(uploaded.name, uploaded.getvalue()) for uploaded in files]

    def on_progress(completed: int, all_items: int, current_name: str) -> None:
        status_box.info(f"Completed {completed}/{all_items}: `{current_name}`")
        progress.progress(completed / all_items, text=f"Completed {completed}/{all_items}")

    results = process_files_parallel(
        payloads,
        target_format=target_format,
        options=options,
        max_workers=workers,
        use_processes=False,
        progress_callback=on_progress,
    )

    status_box.success("Conversion completed.")
    return results


def render_app() -> None:
    st.set_page_config(page_title="Batch File Converter", page_icon="📂", layout="wide")
    st.title("Batch File Converter")
    st.caption("Upload files, convert in one click, and download output files instantly.")

    top_left, top_right = st.columns([2, 1], vertical_alignment="bottom")
    with top_left:
        uploaded_files = st.file_uploader(
            "Upload files (PDF, PNG, JPG, JPEG, WEBP, BMP, TIFF)",
            type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"],
            accept_multiple_files=True,
        )
    with top_right:
        target_format = st.selectbox("Output format", SUPPORTED_FORMATS, index=0)

    controls_col, helper_col = st.columns([1, 1], vertical_alignment="center")
    with controls_col:
        convert_clicked = st.button("Convert Files", type="primary", use_container_width=True)
    with helper_col:
        if uploaded_files:
            st.caption(f"Ready: {len(uploaded_files)} file(s) selected")
        else:
            st.caption("No files selected yet")

    worker_limit = max(1, min(32, (cpu_count() or 4) * 2))
    worker_default = min(8, worker_limit)
    workers = st.slider(
        "Parallel workers",
        min_value=1,
        max_value=worker_limit,
        value=worker_default,
        help="Higher values can speed up large batches.",
    )

    st.subheader("Power Settings")
    s1, s2, s3 = st.columns(3)
    with s1:
        resize_enabled = st.checkbox("Enable resize", value=False)
        keep_aspect_ratio = st.checkbox("Keep aspect ratio", value=True, disabled=not resize_enabled)
    with s2:
        resize_width = st.number_input(
            "Resize width",
            min_value=1,
            max_value=10000,
            value=1920,
            disabled=not resize_enabled,
        )
        resize_height = st.number_input(
            "Resize height",
            min_value=1,
            max_value=10000,
            value=1080,
            disabled=not resize_enabled,
        )
    with s3:
        pdf_dpi = st.slider("PDF DPI", min_value=72, max_value=400, value=200, step=8)

    quality = 85
    png_compress_level = 6
    png_optimize = True
    webp_lossless = False

    if target_format in {"jpg", "webp"}:
        quality = st.slider(
            f"{target_format.upper()} quality",
            min_value=1,
            max_value=100,
            value=85,
        )
    if target_format == "png":
        png_compress_level = st.slider(
            "PNG compression level",
            min_value=0,
            max_value=9,
            value=6,
        )
        png_optimize = st.checkbox("PNG optimize", value=True)
    if target_format == "webp":
        webp_lossless = st.checkbox("WEBP lossless", value=False)

    if "results" not in st.session_state:
        st.session_state.results = []
    if "zip_bytes" not in st.session_state:
        st.session_state.zip_bytes = b""
    if "target_format" not in st.session_state:
        st.session_state.target_format = target_format

    if convert_clicked:
        if not uploaded_files:
            st.warning("Upload at least one file before converting.")
        else:
            options = ProcessingOptions(
                resize_enabled=resize_enabled,
                resize_width=int(resize_width) if resize_enabled else None,
                resize_height=int(resize_height) if resize_enabled else None,
                keep_aspect_ratio=keep_aspect_ratio,
                quality=quality,
                png_compress_level=png_compress_level,
                png_optimize=png_optimize,
                webp_lossless=webp_lossless,
                pdf_dpi=pdf_dpi,
            )
            results = _convert_uploaded_files(
                uploaded_files,
                target_format,
                workers=workers,
                options=options,
            )
            st.session_state.results = results
            st.session_state.zip_bytes = _build_zip(results)
            st.session_state.target_format = target_format

    results: list[ProcessResult] = st.session_state.results
    if not results:
        return

    success_count = sum(1 for item in results if item.success)
    failure_count = len(results) - success_count

    st.divider()
    st.subheader("Conversion Results")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Files", len(results))
    m2.metric("Success", success_count)
    m3.metric("Failed", failure_count)

    if success_count > 0:
        st.download_button(
            label="Download All (ZIP)",
            data=st.session_state.zip_bytes,
            file_name=f"converted_files_{st.session_state.target_format}.zip",
            mime="application/zip",
            use_container_width=True,
        )

    for index, result in enumerate(results, start=1):
        status_text = "SUCCESS" if result.success else "FAILED"
        with st.container(border=True):
            left, right = st.columns([3, 1], vertical_alignment="center")
            with left:
                st.markdown(f"**{index}. {result.source_name}**")
                st.caption(f"Type: {result.file_type or 'unknown'}")
            with right:
                st.write(f"`{status_text}`")

            if result.message:
                st.error(result.message)

            if result.success and result.outputs:
                st.success(f"Generated {len(result.outputs)} output file(s).")
                for output_index, output in enumerate(result.outputs, start=1):
                    st.download_button(
                        label=f"Download {output.filename}",
                        data=output.content,
                        file_name=output.filename,
                        mime="application/octet-stream",
                        key=f"dl-{index}-{output_index}",
                    )


if __name__ == "__main__":
    render_app()
