"""M3 editor and report smoke tests."""

from __future__ import annotations

from app.audit import audit_all
from app.db import connect, init_db
from app.editor import run_demo_edit
from app.media import ensure_demo_media
from app.report import generate_job_report
from app.seed import seed_demo


def test_edit_and_report(tmp_path):
    db_path = tmp_path / "demo.db"
    init_db(db_path)
    seed_demo(db_path)
    audit_all(db_path)
    ensure_demo_media()

    output = run_demo_edit(db_path)
    assert output.exists()

    conn = connect(db_path)
    job = conn.execute("SELECT id FROM edit_jobs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert job is not None

    paths = generate_job_report(db_path, job["id"])
    for path in paths.values():
        assert path.exists()

    conn = connect(db_path)
    report_count = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
    conn.close()
    assert report_count == 3
