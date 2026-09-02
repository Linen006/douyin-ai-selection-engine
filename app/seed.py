"""Load built-in sample data into a local database."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import SAMPLE_DIR
from app.db import connect

PRODUCTS_FILE = SAMPLE_DIR / "products.json"
MATERIALS_FILE = SAMPLE_DIR / "materials.json"


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_demo(db_path: Path | str) -> dict:
    """Insert sample products and materials; return inserted row counts."""
    conn = connect(db_path)
    products = _load(PRODUCTS_FILE)
    materials = _load(MATERIALS_FILE)

    product_ids: dict[str, int] = {}
    for item in products:
        cursor = conn.execute(
            """
            INSERT INTO products
                (sample_key, title, url, image_path, category, price,
                 shop_count, week_sales, video_sales_ratio, conversion_rate,
                 launch_days, remark, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                item.get("sample_key"),
                item["title"],
                item.get("url", ""),
                item.get("image_path", ""),
                item.get("category", ""),
                item.get("price"),
                item.get("shop_count"),
                item.get("week_sales"),
                item.get("video_sales_ratio"),
                item.get("conversion_rate"),
                item.get("launch_days"),
                item.get("remark", ""),
            ),
        )
        if item.get("sample_key"):
            product_ids[item["sample_key"]] = cursor.lastrowid

    material_rows = 0
    for item in materials:
        product_id = product_ids.get(item.get("sample_key", ""))
        if product_id is None:
            continue
        conn.execute(
            """
            INSERT INTO materials
                (product_id, source, title, video_path, likes, comments,
                 publish_days, transcript, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                product_id,
                item.get("source", "demo"),
                item.get("title", ""),
                item.get("video_file", ""),
                item.get("likes", 0),
                item.get("comments", 0),
                item.get("publish_days"),
                item.get("transcript", ""),
            ),
        )
        material_rows += 1

    conn.commit()
    conn.close()
    return {"products": len(products), "materials": material_rows}
