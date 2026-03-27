from __future__ import annotations

import time
from os import cpu_count
from pathlib import Path

import streamlit as st

from core.job_manager import ConversionJob, JobFileRecord, create_job, get_job
from core.processing import ProcessingOptions

SUPPORTED_FORMATS = ("png", "jpg", "webp")
ACTIVE_STATES = {"pending", "processing"}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            }
            .block-container {
                max-width: 960px;
                padding-top: 2rem;
                padding-bottom: 3rem;
            }
            .hero-title {
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
                color: #0f172a;
            }
            .hero-subtitle {
                color: #334155;
                margin-bottom: 1rem;
            }
            .section-label {
                font-size: 0.85rem;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.25rem;
            }
            .result-success {
                background: rgba(22, 163, 74, 0.08);
                border: 1px solid rgba(22, 163, 74, 0.25);
                border-radius: 10px;
                padding: 0.4rem 0.7rem;
                color: #166534;
                font-weight: 600;
            }
            .result-failed {
                background: rgba(220, 38, 38, 0.08);
                border: 1px solid rgba(220, 38, 38, 0.25);
                border-radius: 10px;
                padding: 0.4rem 0.7rem;
                color: #991b1b;
                font-weight: 600;
            }
            @media (prefers-color-scheme: dark) {
                .stApp {
                    background: linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
                }
                .hero-title {
                    color: #e2e8f0;
                }
                .hero-subtitle, .section-label {
                    color: #94a3b8;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_badge(status: str) -> str:
    return {
        "pending": "PENDING",
        "processing": "PROCESSING",
        "done": "DONE",
        "failed": "FAILED",
    }.get(status, status.upper())


def _render_uploaded_file_list(uploaded_files) -> None:
    st.markdown('<div class="section-label">Uploaded Files</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if not uploaded_files:
            st.caption("No files uploaded yet.")
            return
        for index, item in enumerate(uploaded_files, start=1):
            size_kb = len(item.getvalue()) / 1024
            st.write(f"{index}. `{item.name}`  •  {size_kb:.1f} KB")


def _render_results(files: list[JobFileRecord], zip_path: str, target_format: str, job_id: str) -> None:
    success_count = sum(1 for item in files if item.status == "done")
    failure_count = len(files) - success_count

    st.divider()
    st.subheader("Conversion Results")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Files", len(files))
    m2.metric("Success", success_count)
    m3.metric("Failed", failure_count)

    if success_count > 0 and zip_path and Path(zip_path).exists():
        st.download_button(
            label="Download All (ZIP)",
            data=Path(zip_path).read_bytes(),
            file_name=f"converted_files_{target_format}_{job_id}.zip",
            mime="application/zip",
            use_container_width=True,
        )

    for index, record in enumerate(files, start=1):
        status_text = "SUCCESS" if record.status == "done" else "FAILED"
        with st.container(border=True):
            left, right = st.columns([3, 1], vertical_alignment="center")
            with left:
                st.markdown(f"**{index}. {record.source_name}**")
                st.caption(f"Type: {record.file_type or 'unknown'}")
            with right:
                css_class = "result-success" if record.status == "done" else "result-failed"
                st.markdown(
                    f'<div class="{css_class}">{status_text}</div>',
                    unsafe_allow_html=True,
                )

            if record.message:
                st.error(record.message)

            if record.status == "done" and record.output_paths:
                st.success(f"Generated {len(record.output_paths)} output file(s).")
                for output_index, path_str in enumerate(record.output_paths, start=1):
                    output_path = Path(path_str)
                    if not output_path.exists():
                        continue
                    st.download_button(
                        label=f"Download {output_path.name}",
                        data=output_path.read_bytes(),
                        file_name=output_path.name,
                        mime="application/octet-stream",
                        key=f"dl-{job_id}-{index}-{output_index}",
                    )


def render_app() -> None:
    st.set_page_config(page_title="Batch File Converter", page_icon="📂", layout="centered")
    _inject_styles()

    st.markdown('<div class="hero-title">Batch File Converter</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Convert PDFs and images in a clean background-job workflow. '
        "Create a job, track progress, and download outputs in one place.</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("#### Conversion Setup")
        top_left, top_right = st.columns([2, 1], vertical_alignment="bottom")
        with top_left:
            uploaded_files = st.file_uploader(
                "Upload files (PDF, PNG, JPG, JPEG, WEBP, BMP, TIFF)",
                type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"],
                accept_multiple_files=True,
            )
        with top_right:
            target_format = st.selectbox("Format", SUPPORTED_FORMATS, index=0)

        controls_col, helper_col = st.columns([1, 1], vertical_alignment="center")
        with controls_col:
            convert_clicked = st.button("Start Conversion", type="primary", use_container_width=True)
        with helper_col:
            if uploaded_files:
                st.caption(f"Ready: {len(uploaded_files)} file(s)")
            else:
                st.caption("No files selected")

        _render_uploaded_file_list(uploaded_files)

        worker_limit = max(1, min(32, (cpu_count() or 4) * 2))
        worker_default = min(8, worker_limit)
        workers = st.slider(
            "Parallel workers",
            min_value=1,
            max_value=worker_limit,
            value=worker_default,
            help="Higher values can speed up large batches.",
        )

        with st.expander("Advanced Settings", expanded=False):
            s1, s2, s3 = st.columns(3)
            with s1:
                resize_enabled = st.checkbox("Enable resize", value=False)
                keep_aspect_ratio = st.checkbox(
                    "Keep aspect ratio",
                    value=True,
                    disabled=not resize_enabled,
                )
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

    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = ""

    if convert_clicked:
        if not uploaded_files:
            st.warning("Upload at least one file before creating a job.")
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

    st.markdown('<div class="section-label">Job Monitor</div>', unsafe_allow_html=True)
    with st.container(border=True):
        active_job_id = st.text_input(
            "Job ID",
            value=st.session_state.active_job_id,
            help="Paste a job ID to monitor status after refresh.",
        ).strip()
        st.session_state.active_job_id = active_job_id

        if not active_job_id:
            st.caption("Create a job above or paste an existing job ID.")
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

        _render_results(job.files, job.zip_path, job.target_format, job.job_id)


if __name__ == "__main__":
    render_app()
