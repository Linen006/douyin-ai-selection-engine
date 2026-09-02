"""Locate ffmpeg/ffprobe without hard-coding a machine path."""

from __future__ import annotations

import os
import shutil
from typing import Optional


def find_ffmpeg() -> Optional[str]:
    configured = os.getenv("FFMPEG_BIN", "").strip()
    if configured:
        return configured
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def find_ffprobe() -> Optional[str]:
    configured = os.getenv("FFPROBE_BIN", "").strip()
    if configured:
        return configured
    found = shutil.which("ffprobe")
    return found or None
