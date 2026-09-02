"""M0 smoke tests: schema, sample seed data, ffmpeg discovery."""

from __future__ import annotations

import json

from app.config import SAMPLE_DIR
from app.db import connect, init_db, table_names
from app.ffmpeg import find_ffmpeg
from app.seed import seed_demo

EXPECTED_TABLES = {
    "products",
    "score_details",
    "materials",
    "audit_checks",
    "review_tasks",
    "edit_jobs",
    "edit_clips",
    "reports",
}


def test_init_db_creates_all_tables(tmp_path):
    db_path = tmp_path / "demo.db"
    conn = init_db(db_path)
    assert EXPECTED_TABLES <= set(table_names(conn))
    conn.close()


def test_seed_inserts_sample_rows(tmp_path):
    db_path = tmp_path / "demo.db"
    init_db(db_path)
    counts = seed_demo(db_path)

    products = json.loads((SAMPLE_DIR / "products.json").read_text(encoding="utf-8"))
    assert counts["products"] == len(products)
    assert counts["materials"] > 0

    conn = connect(db_path)
    materials = conn.execute("SELECT video_path FROM materials").fetchall()
    assert all(row["video_path"].endswith(".mp4") for row in materials)
    conn.close()


def test_ffmpeg_is_discoverable():
    exe = find_ffmpeg()
    assert exe, "ffmpeg should be discoverable via PATH or imageio-ffmpeg"
