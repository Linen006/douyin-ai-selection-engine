"""Rule-based material compliance audit.

The M2 scope works on transcript/metadata text and produces explainable
checks. Uncertain cases are routed to a human review queue.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from app.ai import get_ai_client
from app.db import connect


@dataclass
class AuditCheck:
    check_name: str
    evidence: str
    risk_level: str
    decision: str


@dataclass
class MaterialAuditResult:
    material_id: int
    title: str
    status: str
    risk_level: str
    checks: list[AuditCheck] = field(default_factory=list)


PRICE_KEYWORDS = ["9.9元", "19.9元", "9.9", "19.9", "秒杀", "最低价", "优惠价"]
EXTREME_KEYWORDS = ["最", "第一", "顶级", "唯一", "绝对", "100%"]
EFFICACY_KEYWORDS = ["治疗", "疾病", "美白", "祛斑", "改善", "虚假效果", "效果显著"]
CELEBRITY_KEYWORDS = ["明星", "网红", "直播切片", "影视人物"]
WATERMARK_KEYWORDS = ["博主昵称", "平台水印", "防伪水印", "昵称"]
AB_GOODS_KEYWORDS = ["升级款", "标准款", "实际发货", "不同款", "换款"]

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _matched(keywords: list[str], text: str) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def audit_text(text: str) -> list[AuditCheck]:
    """Run all rule checks against one material transcript."""
    checks: list[AuditCheck] = []

    price_hits = _matched(PRICE_KEYWORDS, text)
    if price_hits:
        checks.append(AuditCheck("价格内容", "命中：" + "、".join(price_hits), "medium", "reject"))

    extreme_hits = _matched(EXTREME_KEYWORDS, text)
    if extreme_hits:
        checks.append(AuditCheck("极限词", "命中：" + "、".join(extreme_hits), "high", "reject"))

    efficacy_hits = _matched(EFFICACY_KEYWORDS, text)
    if efficacy_hits:
        checks.append(AuditCheck("功效夸大", "命中：" + "、".join(efficacy_hits), "high", "reject"))

    celebrity_hits = _matched(CELEBRITY_KEYWORDS, text)
    if celebrity_hits:
        checks.append(AuditCheck("明星/网红", "命中：" + "、".join(celebrity_hits), "high", "reject"))

    watermark_hits = _matched(WATERMARK_KEYWORDS, text)
    if watermark_hits:
        checks.append(AuditCheck("水印", "命中：" + "、".join(watermark_hits), "medium", "reject"))

    ab_hits = _matched(AB_GOODS_KEYWORDS, text)
    if ab_hits:
        checks.append(AuditCheck("AB货风险", "命中：" + "、".join(ab_hits), "high", "manual"))

    return checks


def _combine(checks: list[AuditCheck]) -> tuple[str, str]:
    if not checks:
        return "approved", "low"
    risk_level = max((check.risk_level for check in checks), key=lambda level: RISK_ORDER[level])
    if any(check.decision == "reject" for check in checks):
        return "rejected", risk_level
    if any(check.decision == "manual" for check in checks):
        return "manual", risk_level
    return "approved", risk_level


def _persist_checks(conn: sqlite3.Connection, material_id: int, checks: list[AuditCheck]) -> None:
    for check in checks:
        conn.execute(
            """
            INSERT INTO audit_checks
                (material_id, check_name, evidence, risk_level, decision)
            VALUES (?, ?, ?, ?, ?)
            """,
            (material_id, check.check_name, check.evidence, check.risk_level, check.decision),
        )


def audit_all(db_path: Path | str) -> list[MaterialAuditResult]:
    """Audit every material and persist checks, status, and review tasks."""
    conn = connect(db_path)
    conn.execute("DELETE FROM audit_checks")
    conn.execute("DELETE FROM review_tasks")

    rows = conn.execute(
        """
        SELECT m.*, p.title AS product_title
        FROM materials m
        JOIN products p ON p.id = m.product_id
        ORDER BY m.id
        """
    ).fetchall()

    ai_client = get_ai_client()
    results: list[MaterialAuditResult] = []
    for row in rows:
        checks = audit_text(row["transcript"])
        status, risk_level = _combine(checks)
        _persist_checks(conn, row["id"], checks)
        conn.execute(
            "UPDATE materials SET status = ? WHERE id = ?",
            (status, row["id"]),
        )
        if status == "manual":
            reason = "；".join(check.evidence for check in checks if check.decision == "manual")
            cursor = conn.execute(
                """
                INSERT INTO review_tasks
                    (source_type, source_id, reason, status)
                VALUES ('material', ?, ?, 'pending')
                """,
                (row["id"], reason),
            )
            checks_text = "；".join(f"{check.check_name}:{check.evidence}" for check in checks)
            suggestion = ai_client.review_suggestion(
                row["title"], row["transcript"], checks_text
            )
            ai_note = (
                f"{suggestion.get('decision', 'manual')}|{suggestion.get('reason', '')}"
            )
            conn.execute(
                "UPDATE review_tasks SET ai_note = ? WHERE id = ?",
                (ai_note, cursor.lastrowid),
            )
        results.append(
            MaterialAuditResult(
                material_id=row["id"],
                title=row["title"],
                status=status,
                risk_level=risk_level,
                checks=checks,
            )
        )

    conn.commit()
    conn.close()
    return results
