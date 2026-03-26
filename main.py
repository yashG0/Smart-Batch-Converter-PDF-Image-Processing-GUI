from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from core.processing import ProcessResult, process_file

SUPPORTED_FORMATS = ("png", "jpg", "webp")


def _build_zip(results: list[ProcessResult]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for result in results:
            if not result.success:
                continue
            for output in result.outputs:
                archive.writestr(output.filename, output.content)
    return buffer.getvalue()


def _convert_uploaded_files(files, target_format: str) -> list[ProcessResult]:
    results: list[ProcessResult] = []
    for uploaded in files:
        result = process_file(
            name=uploaded.name,
            content=uploaded.getvalue(),
            target_format=target_format,
        )
        results.append(result)
    return results


def render_app() -> None:
    st.set_page_config(page_title="Batch File Converter", page_icon="📂", layout="wide")
    st.title("Batch File Converter")
    st.caption("Upload PDFs or images, convert in one click, and download outputs.")

    uploaded_files = st.file_uploader(
        "Upload files (PDF, PNG, JPG, JPEG, WEBP, BMP, TIFF)",
        type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        accept_multiple_files=True,
    )
    target_format = st.selectbox("Select output format", SUPPORTED_FORMATS, index=0)

    if "results" not in st.session_state:
        st.session_state.results = []
    if "zip_bytes" not in st.session_state:
        st.session_state.zip_bytes = b""
    if "target_format" not in st.session_state:
        st.session_state.target_format = target_format

    if st.button("Convert", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Upload at least one file before converting.")
        else:
            results = _convert_uploaded_files(uploaded_files, target_format)
            st.session_state.results = results
            st.session_state.zip_bytes = _build_zip(results)
            st.session_state.target_format = target_format

    results: list[ProcessResult] = st.session_state.results
    if not results:
        return

    success_count = sum(1 for item in results if item.success)
    failure_count = len(results) - success_count

    st.subheader("Results")
    st.write(
        f"Processed `{len(results)}` file(s): `{success_count}` success, `{failure_count}` failed."
    )

    if success_count > 0:
        st.download_button(
            label="Download All (ZIP)",
            data=st.session_state.zip_bytes,
            file_name=f"converted_files_{st.session_state.target_format}.zip",
            mime="application/zip",
            use_container_width=True,
        )

    for index, result in enumerate(results, start=1):
        header = f"{index}. {result.source_name}"
        with st.expander(header, expanded=False):
            st.write(f"Type: `{result.file_type or 'unknown'}`")
            st.write(f"Status: `{'success' if result.success else 'failed'}`")
            if result.message:
                st.write(f"Message: {result.message}")

            if result.success and result.outputs:
                st.write(f"Generated {len(result.outputs)} output file(s).")
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
