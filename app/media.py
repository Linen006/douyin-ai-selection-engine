"""Generate tiny synthetic clips so demo editing needs no real footage."""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import MEDIA_DIR, ensure_dirs
from app.ffmpeg import find_ffmpeg

DEMO_CLIPS = [
    "demo_01.mp4",
    "demo_02.mp4",
    "demo_03.mp4",
    "demo_04.mp4",
    "demo_05.mp4",
    "demo_06.mp4",
]


def _build_command(exe: str, out_path: Path, frequency: int, duration: int = 4) -> list[str]:
    return [
        exe,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size=640x360:rate=24:duration={duration}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequency}:duration={duration}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(out_path),
    ]


def ensure_demo_media(force: bool = False) -> list[str]:
    """Create missing demo clips and return the names that were generated."""
    ensure_dirs()
    exe = find_ffmpeg()
    if exe is None:
        raise RuntimeError("ffmpeg not found; install it or run pip install imageio-ffmpeg")

    created: list[str] = []
    for index, name in enumerate(DEMO_CLIPS, start=1):
        out_path = MEDIA_DIR / name
        if out_path.exists() and not force:
            continue
        command = _build_command(exe, out_path, frequency=300 + index * 40)
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {name}: {proc.stderr[-500:]}")
        created.append(name)
    return created
