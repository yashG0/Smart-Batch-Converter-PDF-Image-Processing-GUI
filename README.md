# 📄 Batch File Converter (PDF & Image)

A local-first document processing application built with **Python** and **Streamlit** for high-performance batch conversion of PDFs and images.

The application supports parallel processing, smart file validation, background job management, and configurable conversion options while maintaining a clean, extensible architecture through a plugin-based processing engine.

---

## ✨ Features

### 📂 Batch Processing

- Convert multiple files simultaneously
- Parallel conversion engine
- Background job queue
- ZIP download for processed files
- Per-file conversion status

### 📄 PDF Conversion

- PDF → PNG
- PDF → JPG
- PDF → WEBP

### 🖼 Image Conversion

- PNG → JPG
- JPG → PNG
- WEBP → PNG
- Image → PDF

### ⚙ Smart Processing

- Automatic file type detection
- File validation
- Resize options
- Compression controls
- Format-specific conversion settings

### 🗃 Job Management

- Background job queue
- Job IDs
- SQLite persistence
- Progress tracking

### 🧩 Extensible Architecture

- Plugin-based conversion handlers
- Easily add new file formats
- Modular processing pipeline

---

## 📸 Screenshots

### Dashboard

![Dashboard](assets/screenshots/ui_dashboard.png)

### Conversion Results

![Results](assets/screenshots/ui_results.png)

---

## 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Programming Language |
| Streamlit | User Interface |
| Pillow | Image Processing |
| PyMuPDF | PDF Rendering |
| img2pdf | PDF Generation |
| SQLite | Job Metadata Storage |
| uv | Package Management |
| pytest | Testing |

---

## 📂 Project Structure

```text
.
├── assets/
│   ├── examples/
│   └── screenshots/
├── core/
│   ├── image_handler.py
│   ├── pdf_handler.py
│   └── utils.py
├── services/
│   ├── jobs/
│   └── processing/
├── ui/
│   └── app.py
├── tests/
├── main.py
├── benchmark.py
├── pyproject.toml
└── README.md
```

---

## ⚙ Getting Started

### Clone Repository

```bash
git clone https://github.com/yashG0/batch-file-converter.git

cd batch-file-converter
```

### Install Dependencies

```bash
uv sync
```

### Run Application

```bash
uv run streamlit run main.py
```

---

## 📊 Architecture

```text
User

      │

      ▼

Streamlit UI

      │

      ▼

Processing Service

      │

      ▼

Conversion Registry

      │

      ▼

PDF / Image Handlers

      │

      ▼

Output Files
```

---

## 🧩 Plugin System

New conversion handlers can be registered without modifying the processing engine.

```python
from services.processing import register_handler

def docx_handler(name, content, target_format, options):
    ...

register_handler(
    "docx",
    docx_handler,
    extensions=(".docx",),
)
```

Built-in handlers are available for:

- PDF
- Images

---

## 🧪 Testing

Run all tests

```bash
uv run pytest
```

Generate coverage report

```bash
uv run pytest \
--cov=services \
--cov=core \
--cov=ui \
--cov-report=term-missing
```

---

## 🚀 Performance Benchmark

Run a local benchmark

```bash
uv run python benchmark.py
```

---

## 🛡 Edge Cases

- Empty files
- Corrupted PDFs
- Corrupted images
- Unsupported file formats
- Duplicate output filenames
- Parallel worker failures
- SQLite job persistence

---

## 🎯 Why I Built This

This project was built to explore scalable file-processing workflows using Python. The goal was to design a modular conversion system capable of handling large batches efficiently while maintaining clean architecture, extensibility, and reliable error handling.

---

## 🚀 Future Improvements

- Docker support
- OCR support
- Drag-and-drop uploads
- Cloud storage integration
- Progress bars
- User authentication
- Distributed workers
- PDF optimization
- Video conversion plugins

---

## 👨‍💻 Author

**Yash Gaurkar**

- GitHub: https://github.com/yashG0
- LinkedIn: https://linkedin.com/in/yash-gaurkar-a897b3228
- Portfolio: https://yash-portfolio-app.vercel.app

---

⭐ If you found this project useful, consider giving it a **Star**.
