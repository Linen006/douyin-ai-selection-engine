"""Simple ffmpeg-based editing for the demo.

M3 keeps editing conservative: approved clips are trimmed to a short segment,
normalized, then concatenated into one output video with an editable plan.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from app.config import DATA_DIR, MEDIA_DIR
from app.db import connect
from app.ffmpeg import find_ffmpeg

OUTPUT_DIR = DATA_DIR / "output"
TMP_DIR = OUTPUT_DIR / "tmp"
SEGMENT_SECONDS = 3.0


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def probe_duration(path: Path) -> float:
    """Return media duration in seconds, or 0.0 when it cannot be parsed."""
    exe = find_ffmpeg()
    if exe is None:
        return 0.0
    proc = _run([exe, "-hide_banner", "-i", str(path)])
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr or "")
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def create_edit_job(conn) -> int:
    """Create a montage job from all approved materials."""
    rows = conn.execute(
        """
        SELECT id, product_id, video_path
        FROM materials
        WHERE status = 'approved'
        ORDER BY id
        """
    ).fetchall()
    if not rows:
        raise RuntimeError("没有已通过审核的素材，无法创建剪辑任务")

    segments = []
    for position, row in enumerate(rows, start=1):
        source_path = MEDIA_DIR / row["video_path"]
        duration = probe_duration(source_path)
        end_sec = min(SEGMENT_SECONDS, duration) if duration > 0 else SEGMENT_SECONDS
        segments.append(
            {
                "position": position,
                "material_id": row["id"],
                "source": str(source_path),
                "start_sec": 0.0,
                "end_sec": round(end_sec, 2),
            }
        )

    cursor = conn.execute(
        """
        INSERT INTO edit_jobs
            (product_id, plan_json, status, output_path)
        VALUES (?, ?, 'planned', '')
        """,
        (rows[0]["product_id"], json.dumps(segments, ensure_ascii=False)),
    )
    job_id = cursor.lastrowid

    for segment in segments:
        conn.execute(
            """
            INSERT INTO edit_clips
                (job_id, material_id, start_sec, end_sec, position)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                job_id,
                segment["material_id"],
                segment["start_sec"],
                segment["end_sec"],
                segment["position"],
            ),
        )
    conn.commit()
    return job_id


def render_edit_job(conn, job_id: int) -> Path:
    """Normalize and concatenate the clips referenced by a job."""
    exe = find_ffmpeg()
    if exe is None:
        raise RuntimeError("ffmpeg not found; install it or run pip install imageio-ffmpeg")

    rows = conn.execute(
        """
        SELECT ec.position, ec.start_sec, ec.end_sec, m.video_path
        FROM edit_clips ec
        JOIN materials m ON m.id = ec.material_id
        WHERE ec.job_id = ?
        ORDER BY ec.position
        """,
        (job_id,),
    ).fetchall()

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    segment_files: list[Path] = []
    for row in rows:
        source = MEDIA_DIR / row["video_path"]
        output = TMP_DIR / f"seg_{row['position']:02d}.mp4"
        duration = max(0.1, float(row["end_sec"]) - float(row["start_sec"]))
        command = [
            exe,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(row["start_sec"]),
            "-t",
            str(duration),
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output),
        ]
        proc = _run(command)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg segment failed: {proc.stderr[-500:]}")
        segment_files.append(output)

    concat_file = TMP_DIR / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.as_posix()}'" for path in segment_files),
        encoding="utf-8",
    )

    final_path = OUTPUT_DIR / f"final_{job_id}.mp4"
    concat_command = [
        exe,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(final_path),
    ]
    proc = _run(concat_command)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[-500:]}")

    conn.execute(
        """
        UPDATE edit_jobs
        SET status = 'done', output_path = ?, completed_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (str(final_path), job_id),
    )
    conn.commit()
    return final_path


def run_demo_edit(db_path: Path | str) -> Path:
    conn = connect(db_path)
    try:
        job_id = create_edit_job(conn)
        return render_edit_job(conn, job_id)
    finally:
        conn.close()
