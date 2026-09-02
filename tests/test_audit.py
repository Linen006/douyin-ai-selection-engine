"""M2 material audit and review tests."""

from __future__ import annotations

import pytest

from app.audit import audit_all, audit_text
from app.db import connect, init_db
from app.review import resolve_task
from app.seed import seed_demo


@pytest.fixture()
def seeded_db(tmp_path):
    db_path = tmp_path / "demo.db"
    init_db(db_path)
    seed_demo(db_path)
    return db_path


def test_audit_text_detects_price_extreme_and_celebrity():
    checks = audit_text("这款清洁刷现在只要9.9元，全网最低价，绝对好用，明星网红都在推荐。")
    names = {check.check_name for check in checks}
    assert {"价格内容", "极限词", "明星/网红"} <= names


def test_ab_goods_routes_to_manual_review():
    checks = audit_text("视频展示的是升级款，实际发货标准款，请人工核对。")
    assert any(check.check_name == "AB货风险" and check.decision == "manual" for check in checks)


def test_audit_all_persists_statuses_and_review_queue(seeded_db):
    results = audit_all(seeded_db)
    assert len(results) == 6

    conn = connect(seeded_db)
    statuses = {row["status"] for row in conn.execute("SELECT status FROM materials")}
    review_count = conn.execute("SELECT COUNT(*) AS n FROM review_tasks").fetchone()["n"]
    check_count = conn.execute("SELECT COUNT(*) AS n FROM audit_checks").fetchone()["n"]
    conn.close()

    assert "rejected" in statuses
    assert "manual" in statuses
    assert "approved" in statuses
    assert review_count == 1
    assert check_count > 0


def test_resolve_task_updates_material(seeded_db):
    audit_all(seeded_db)
    conn = connect(seeded_db)
    task = conn.execute(
        "SELECT * FROM review_tasks WHERE status = 'pending' LIMIT 1"
    ).fetchone()
    conn.close()
    assert task is not None

    assert resolve_task(seeded_db, task["id"], True, note="人工核对通过")

    conn = connect(seeded_db)
    material = conn.execute(
        "SELECT status FROM materials WHERE id = ?", (task["source_id"],)
    ).fetchone()
    task_after = conn.execute(
        "SELECT status FROM review_tasks WHERE id = ?", (task["id"],)
    ).fetchone()
    conn.close()

    assert material["status"] == "approved"
    assert task_after["status"] == "approved"
