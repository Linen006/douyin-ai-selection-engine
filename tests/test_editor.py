"""M3 editor and report smoke tests."""

from __future__ import annotations

from app.audit import audit_all
from app.db import connect, init_db
from app.editor import create_edit_job, run_demo_edit
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


def test_create_edit_job_keeps_materials_within_one_product(tmp_path, monkeypatch):
    """One edit job must never combine approved materials from different products."""
    db_path = tmp_path / "demo.db"
    init_db(db_path)
    seed_demo(db_path)

    conn = connect(db_path)
    rows = conn.execute(
        "SELECT id, product_id FROM materials ORDER BY product_id, id"
    ).fetchall()
    first_product = rows[0]["product_id"]
    other_product = next(row["product_id"] for row in rows if row["product_id"] != first_product)
    conn.execute(
        "UPDATE materials SET status = 'approved' WHERE product_id IN (?, ?)",
        (first_product, other_product),
    )
    conn.commit()

    monkeypatch.setattr("app.editor.probe_duration", lambda _path: 4.0)
    job_id = create_edit_job(conn)

    job = conn.execute(
        "SELECT product_id FROM edit_jobs WHERE id = ?", (job_id,)
    ).fetchone()
    clip_products = {
        row["product_id"]
        for row in conn.execute(
            """
            SELECT m.product_id
            FROM edit_clips ec
            JOIN materials m ON m.id = ec.material_id
            WHERE ec.job_id = ?
            """,
            (job_id,),
        )
    }
    conn.close()

    assert job["product_id"] == first_product
    assert clip_products == {first_product}
