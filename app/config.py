"""Shared paths and runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DIR = DATA_DIR / "sample"
MEDIA_DIR = DATA_DIR / "demo" / "media"
DB_PATH = DATA_DIR / "demo.db"

load_dotenv(BASE_DIR / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "").strip()


def ensure_dirs() -> None:
    """Create local data directories used by the app."""
    for path in (SAMPLE_DIR, MEDIA_DIR):
        path.mkdir(parents=True, exist_ok=True)
