# Batch File Converter (PDF & Image)

A local-first Streamlit app for batch converting PDFs and images with smart validation, parallel processing, and power controls.

## Highlights

- Multiple file upload
- PDF -> PNG/JPG/WEBP
- Image -> PNG/JPG/WEBP
- Smart file detection and validation
- Per-file success/failed status
- Parallel batch processing
- ZIP download for all converted outputs
- Power settings: resize, compression, format-specific controls

## Screenshots

### Dashboard

![Dashboard](assets/screenshots/ui_dashboard.png)

### Results

![Results](assets/screenshots/ui_results.png)

## Example Files

Sample test files are included in `assets/examples/`:

- `landscape_demo.png`
- `portrait_demo.jpg`
- `sample_document.pdf` (2 pages)

## Tech Stack

- Python
- Streamlit
- Pillow
- pdf2image
- uv

## Project Structure

```text
.
├── assets/
│   ├── examples/
│   └── screenshots/
├── core/
│   ├── image_handler.py
│   ├── pdf_handler.py
│   ├── processing.py
│   └── utils.py
├── main.py
├── test_core.py
├── test_processing.py
├── pyproject.toml
└── README.md
```

## Installation

1. Install dependencies:

```bash
uv sync
```

2. Install Poppler (required by `pdf2image`):

```bash
sudo pacman -S poppler
```

## Run App

```bash
uv run streamlit run main.py
```

## Run Tests

```bash
uv run python test_core.py
uv run python test_processing.py
```

## Edge Cases Handled

- Empty files
- Unsupported file types
- Corrupted images/PDFs
- Duplicate output file names in ZIP archive
- Parallel worker failures (returns per-file error instead of crashing whole batch)

## Notes

- For very large batches (1000+), increase workers carefully based on machine RAM/CPU.
- Generated files from tests are written under `output/`.
