"""Explainable product scoring based on the requirement document.

The engine first applies hard filters, then scores every product on six
dimensions so even a rejected item can explain why it was rejected.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from app.db import connect


@dataclass
class DimensionScore:
    dimension: str
    score: float
    weight: float
    reason: str


@dataclass
class ScoreResult:
    product_id: int
    title: str
    category: str
    passed: bool
    level: str
    total_score: float
    reject_reasons: list[str] = field(default_factory=list)
    dimensions: list[DimensionScore] = field(default_factory=list)


BLOCKED_CATEGORIES = {
    "大家电",
    "家具",
    "大型设备",
    "珠宝",
    "黄金",
    "手表",
    "品牌独家商品",
    "食品",
    "酒水",
    "生鲜",
    "保健品",
    "化肥",
    "营养液",
    "医疗相关产品",
    "功效美容产品",
    "婴幼儿高风险用品",
}

ALLOWED_CATEGORIES = {
    "个护家清",
    "智能家居",
    "3C数码及配件",
    "服饰内衣",
    "母婴宠物",
    "美妆",
    "玩具乐器",
    "鲜花园艺",
    "运动户外",
    "钟表配饰",
    "图书教育",
}

BLOCKED_KEYWORDS = [
    "品牌独家",
    "旗舰店自研",
    "单店独家",
    "版权",
    "品牌授权",
    "医疗",
    "功效",
    "美白",
    "祛斑",
    "治疗",
    "食品",
    "酒水",
    "生鲜",
    "保健",
    "化肥",
    "营养液",
    "农药",
    "黄金",
    "珠宝",
    "手表",
]

HARD_REJECT_DIMENSION = "硬性淘汰"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _sales_score(product: Mapping) -> DimensionScore:
    ratio = product["video_sales_ratio"] or 0.0
    conv = product["conversion_rate"] or 0.0
    sales = product["week_sales"] or 0

    score = 0.0
    score += 40 if ratio >= 0.7 else 30 if ratio >= 0.5 else 10
    score += 30 if conv >= 0.20 else 24 if conv >= 0.15 else 15 if conv >= 0.10 else 5
    score += 30 if sales >= 5000 else 22 if sales >= 2000 else 12 if sales >= 500 else 4

    reason = (
        f"视频成交占比{ratio * 100:.0f}%，转化率{conv * 100:.0f}%，近7天成交{sales}"
    )
    return DimensionScore("销售表现", _clamp(score), 30, reason)


def _openness_score(product: Mapping) -> DimensionScore:
    shop_count = product["shop_count"] or 0
    score = 100 if shop_count >= 5 else 70 if shop_count >= 3 else 40 if shop_count == 2 else 10
    return DimensionScore("同款开放度", score, 20, f"同款店铺{shop_count}家")


def _growth_score(product: Mapping) -> DimensionScore:
    days = product["launch_days"]
    if days is None:
        return DimensionScore("增长/稳定", 60, 15, "缺少上架天数")
    score = 100 if days <= 30 else 70 if days <= 90 else 50
    return DimensionScore("增长/稳定", score, 15, f"上架{days}天")


def _replicability_score(product: Mapping) -> DimensionScore:
    price = product["price"] or 0.0
    shop_count = product["shop_count"] or 0

    score = 0.0
    if 10 <= price <= 50:
        score += 60
    elif price < 10:
        score += 40
    elif price <= 100:
        score += 30
    else:
        score += 15
    score += 40 if shop_count >= 3 else 25 if shop_count == 2 else 10

    return DimensionScore(
        "可复制性", _clamp(score), 15, f"客单价{price}元，同款店铺{shop_count}家"
    )


def _visual_score(product: Mapping) -> DimensionScore:
    category = product["category"]
    high = {"个护家清", "智能家居", "3C数码及配件", "玩具乐器", "鲜花园艺", "运动户外"}
    medium = {"美妆", "服饰内衣", "母婴宠物", "钟表配饰"}
    score = 100 if category in high else 70 if category in medium else 40
    return DimensionScore("视频可展示性", score, 10, f"类目{category}")


def _compliance_score(product: Mapping) -> DimensionScore:
    text = " ".join([product["title"], product["category"], product["remark"] or ""])
    hits = [keyword for keyword in BLOCKED_KEYWORDS if keyword in text]
    if hits:
        score = max(0, 100 - 25 * len(hits))
        reason = "命中风险词：" + "、".join(hits[:5])
    else:
        score = 100
        reason = "未命中敏感词"
    return DimensionScore("合规风险", score, 10, reason)


SCORE_FUNCTIONS = [
    _sales_score,
    _openness_score,
    _growth_score,
    _replicability_score,
    _visual_score,
    _compliance_score,
]


def hard_filter_reasons(product: Mapping) -> list[str]:
    """Return the reasons that should keep a product out of downstream stages."""
    reasons: list[str] = []

    category = product["category"] or ""
    if category in BLOCKED_CATEGORIES:
        reasons.append(f"命中禁止类目：{category}")
    elif category not in ALLOWED_CATEGORIES:
        reasons.append(f"类目未在可选范围：{category}")

    text = " ".join([product["title"], product["remark"] or ""])
    hits = [keyword for keyword in BLOCKED_KEYWORDS if keyword in text]
    if hits:
        reasons.append("命中禁止关键词：" + "、".join(hits[:5]))

    return reasons


def score_product(product: Mapping) -> ScoreResult:
    dimensions = [func(product) for func in SCORE_FUNCTIONS]
    total_score = sum(item.score * item.weight / 100 for item in dimensions)
    reasons = hard_filter_reasons(product)
    passed = not reasons

    if not passed:
        level = "淘汰"
    elif total_score >= 85:
        level = "S"
    elif total_score >= 70:
        level = "A"
    elif total_score >= 50:
        level = "B"
    else:
        level = "C"

    return ScoreResult(
        product_id=int(product["id"]),
        title=product["title"],
        category=category_of(product),
        passed=passed,
        level=level,
        total_score=round(total_score, 1),
        reject_reasons=reasons,
        dimensions=dimensions,
    )


def category_of(product: Mapping) -> str:
    return product["category"] or ""


def _persist_scores(conn: sqlite3.Connection, results: list[ScoreResult]) -> None:
    conn.execute("DELETE FROM score_details")
    for result in results:
        for item in result.dimensions:
            conn.execute(
                """
                INSERT INTO score_details
                    (product_id, dimension, score, weight, reason, passed)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    result.product_id,
                    item.dimension,
                    item.score,
                    item.weight,
                    item.reason,
                    1,
                ),
            )
        if result.reject_reasons:
            conn.execute(
                """
                INSERT INTO score_details
                    (product_id, dimension, score, weight, reason, passed)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    result.product_id,
                    HARD_REJECT_DIMENSION,
                    0,
                    0,
                    "；".join(result.reject_reasons),
                    0,
                ),
            )
        conn.execute(
            "UPDATE products SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            ("rejected" if not result.passed else "scored", result.product_id),
        )


def score_all(db_path: Path | str) -> list[ScoreResult]:
    conn = connect(db_path)
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    results = [score_product(row) for row in rows]
    _persist_scores(conn, results)
    conn.commit()
    conn.close()
    return results
