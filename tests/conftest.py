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
