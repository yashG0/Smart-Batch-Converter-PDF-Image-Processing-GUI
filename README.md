# 📂 Batch File Converter (PDF & Image)

## 🚀 Overview

Batch File Converter is a modern GUI-based application that enables users to convert multiple PDF and image files into desired formats efficiently.

Built with a clean architecture and powered by a fast Python toolchain, it eliminates the need for repetitive online conversions and ensures privacy through local processing.

---

## 🎯 Features

* 📥 Upload multiple files simultaneously
* 🔄 Convert PDFs → Images (PNG, JPG, WEBP)
* 🖼️ Convert Images → Other formats
* ⚡ Batch processing
* 📦 Download converted files
* 🌐 Modern GUI (browser-based)
* 🔒 Fully offline processing

---

## 🧠 Problem Statement

Most online converters:

* Require manual uploads
* Are inefficient for batch operations
* Raise privacy concerns

This project solves:

* Bulk file conversion
* Offline processing
* Fast, user-friendly workflow

---

## 🛠️ Tech Stack

### Core

* Python 3.11+

### GUI

* `streamlit`

### Processing

* `Pillow (PIL)`
* `pdf2image`

### Tooling

* uv

---

## 🧩 System Design

### High-Level Flow

```id="sysflow01"
User (GUI)
    ↓
File Upload Handler
    ↓
File Type Detection
    ↓
Conversion Engine
   ↙           ↘
PDF Handler   Image Handler
   ↓               ↓
Processed Output (Memory)
    ↓
Download Interface
```

---

## 🏗️ Architecture

```id="arch01"
Presentation Layer (Streamlit)
        ↓
Application Layer
        ↓
Processing Layer
   ├── PDF Service
   └── Image Service
        ↓
Output Layer (Download)
```

---

## 📁 Project Structure

```id="proj01"
batch-converter/
│
├── pyproject.toml        # Managed by uv
├── uv.lock               # Dependency lock file
├── README.md
│
├── app/                  # Application package
│   ├── __init__.py
│   ├── main.py           # Streamlit entry point
│   │
│   ├── core/
│   │   ├── pdf.py        # PDF conversion logic
│   │   ├── image.py      # Image conversion logic
│   │   └── utils.py
│   │
│   └── ui/
│       └── layout.py     # UI components (optional split)
│
└── assets/               # Optional UI/static assets
```

---

## ⚙️ Installation (Using uv)

### 1. Initialize Project

```bash
uv init batch-converter
cd batch-converter
```

---

### 2. Add Dependencies

```bash
uv add streamlit pillow pdf2image
```

---

### 3. Install System Dependency (Linux / CachyOS)

```bash
sudo pacman -S poppler
```

---

### 4. Sync Environment

```bash
uv sync
```

---

## ▶️ Run the Application

```bash
uv run streamlit run app/main.py
```

---

## 🔥 Future Improvements

* 📊 Per-file progress tracking
* 📦 Bulk ZIP download
* ⚡ Parallel processing (multiprocessing)
* 🎨 Improved UI/UX
* 📉 Image compression controls
* 🧠 Smart format suggestions

---

## ⚠️ Limitations

* Large PDFs may consume high memory
* No persistent storage
* Sequential processing (can be optimized)

---

## 💡 Learning Outcomes

* Modern Python project setup using uv
* File and memory handling
* Image & PDF processing
* GUI development
* System design fundamentals

---

## 🏁 Conclusion

This project demonstrates how a real-world problem can be solved using a modern Python stack with clean architecture and efficient tooling.

It bridges the gap between scripting and product-level development.

---
