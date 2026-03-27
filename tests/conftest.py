from __future__ import annotations

from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_sample_image(path: Path, label: str, color: str, size: tuple[int, int] = (320, 180)) -> None:
    image = Image.new("RGB", size, color=color)
    drawer = ImageDraw.Draw(image)
    drawer.text((16, 16), label, fill="white")
    image.save(path)


def create_sample_pdf(path: Path, label: str) -> None:
    first = Image.new("RGB", (420, 240), color="#003049")
    second = Image.new("RGB", (420, 240), color="#d62828")
    ImageDraw.Draw(first).text((24, 24), f"{label} - page 1", fill="white")
    ImageDraw.Draw(second).text((24, 24), f"{label} - page 2", fill="white")
    first.save(path, "PDF", save_all=True, append_images=[second])


@pytest.fixture
def sample_input_dir(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    return input_dir


@pytest.fixture
def sample_image_bytes(sample_input_dir: Path) -> bytes:
    image_path = sample_input_dir / "sample_image.png"
    create_sample_image(image_path, "fixture-image", "#2a9d8f", size=(300, 180))
    return image_path.read_bytes()


@pytest.fixture
def sample_pdf_bytes(sample_input_dir: Path) -> bytes:
    pdf_path = sample_input_dir / "sample_doc.pdf"
    create_sample_pdf(pdf_path, "fixture-pdf")
    return pdf_path.read_bytes()


@pytest.fixture
def unsupported_file_bytes() -> bytes:
    return b"this is plain text and not an image/pdf"


@pytest.fixture
def corrupted_image_bytes() -> bytes:
    return b"not-a-real-image"


@pytest.fixture
def corrupted_pdf_bytes() -> bytes:
    return b"%PDF-broken-content"


@pytest.fixture
def isolated_jobs_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    # Keep job DB/output isolated from repo-level output during tests.
    from services.jobs import storage

    db_path = tmp_path / "jobs.db"
    jobs_root = tmp_path / "jobs"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    monkeypatch.setattr(storage, "JOBS_ROOT", jobs_root)
    storage.init_db()
    return tmp_path
