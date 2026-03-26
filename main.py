from __future__ import annotations

from os import cpu_count
import time

import streamlit as st

from core.job_manager import ConversionJob, create_job, get_job
from core.processing import ProcessResult, ProcessingOptions

SUPPORTED_FORMATS = ("png", "jpg", "webp")
ACTIVE_STATES = {"pending", "processing"}


def _status_badge(status: str) -> str:
    return {
        "pending": "PENDING",
        "processing": "PROCESSING",
        "done": "DONE",
        "failed": "FAILED",
    }.get(status, status.upper())


def _render_results(results: list[ProcessResult], zip_bytes: bytes, target_format: str, job_id: str) -> None:
    success_count = sum(1 for item in results if item.success)
    failure_count = len(results) - success_count

    st.divider()
    st.subheader("Conversion Results")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Files", len(results))
    m2.metric("Success", success_count)
    m3.metric("Failed", failure_count)

    if success_count > 0 and zip_bytes:
        st.download_button(
            label="Download All (ZIP)",
            data=zip_bytes,
            file_name=f"converted_files_{target_format}_{job_id}.zip",
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
                        key=f"dl-{job_id}-{index}-{output_index}",
                    )


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
    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = ""

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
            payloads = [(uploaded.name, uploaded.getvalue()) for uploaded in uploaded_files]
            job_id = create_job(
                payloads=payloads,
                target_format=target_format,
                workers=workers,
                options=options,
            )
            st.session_state.active_job_id = job_id
            st.success(f"Job created: `{job_id}`")

    st.divider()
    st.subheader("Background Job")

    active_job_id = st.text_input(
        "Job ID",
        value=st.session_state.active_job_id,
        help="Paste a job ID to monitor status.",
    ).strip()
    st.session_state.active_job_id = active_job_id

    if not active_job_id:
        return

    job: ConversionJob | None = get_job(active_job_id)
    if job is None:
        st.error("Job not found. Create a new conversion job first.")
        return

    st.write(f"Status: `{_status_badge(job.status)}`")
    if job.status in ACTIVE_STATES:
        total = max(1, job.total_files)
        progress_value = job.processed_files / total
        progress_text = f"{job.processed_files}/{job.total_files} files processed"
        st.progress(progress_value, text=progress_text)
        current = job.current_file or "Waiting for worker"
        st.info(f"Current file: `{current}`")
        time.sleep(0.8)
        st.rerun()

    if job.status == "failed":
        st.error(job.error or "Job failed.")
        return

    results = job.results or []
    _render_results(results, job.zip_bytes, job.target_format, job.job_id)


if __name__ == "__main__":
    render_app()
