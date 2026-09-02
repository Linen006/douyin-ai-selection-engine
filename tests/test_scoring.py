"""M1 scoring engine tests."""

from __future__ import annotations

import pytest

from app.db import connect, init_db
from app.scoring import SCORE_FUNCTIONS, score_all, score_product
from app.seed import seed_demo


@pytest.fixture()
def seeded_db(tmp_path):
    db_path = tmp_path / "demo.db"
    init_db(db_path)
    seed_demo(db_path)
    conn = connect(db_path)
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return db_path, rows


def test_dimension_weights_sum_to_100(seeded_db):
    _, rows = seeded_db
    product = rows[0]
    assert sum(func(product).weight for func in SCORE_FUNCTIONS) == 100


def test_blacklist_products_are_rejected(seeded_db):
    _, rows = seeded_db
    by_key = {row["sample_key"]: row for row in rows}

    teeth = score_product(by_key["teeth-whitening-01"])
    assert teeth.passed is False
    assert teeth.level == "淘汰"
    assert teeth.reject_reasons

    fryer = score_product(by_key["brand-fryer-01"])
    assert fryer.passed is False
    assert fryer.reject_reasons


def test_normal_product_scores_and_passes(seeded_db):
    _, rows = seeded_db
    by_key = {row["sample_key"]: row for row in rows}
    result = score_product(by_key["cleaning-brush-01"])
    assert result.passed is True
    assert result.total_score > 0
    assert result.level in {"S", "A", "B", "C"}


def test_score_all_persists_and_updates_status(seeded_db):
    db_path, _ = seeded_db
    results = score_all(db_path)
    assert len(results) == 7

    conn = connect(db_path)
    score_count = conn.execute("SELECT COUNT(*) AS n FROM score_details").fetchone()["n"]
    statuses = {row["status"] for row in conn.execute("SELECT status FROM products")}
    conn.close()

    assert score_count > 0
    assert "rejected" in statuses
    assert "scored" in statuses
