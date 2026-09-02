"""Generate JSON, Markdown, and HTML risk reports for an edit job."""

from __future__ import annotations

import json
from pathlib import Path

from app.ai import ai_mode
from app.config import DATA_DIR
from app.db import connect

OUTPUT_DIR = DATA_DIR / "output"


def _dict(row) -> dict:
    return {key: row[key] for key in row.keys()}


def _payload(conn, job_id: int) -> dict:
    job = conn.execute("SELECT * FROM edit_jobs WHERE id = ?", (job_id,)).fetchone()
    clips = conn.execute(
        """
        SELECT ec.position, ec.start_sec, ec.end_sec,
               m.title AS material_title, m.status AS material_status,
               p.title AS product_title, p.category AS product_category
        FROM edit_clips ec
        JOIN materials m ON m.id = ec.material_id
        JOIN products p ON p.id = m.product_id
        WHERE ec.job_id = ?
        ORDER BY ec.position
        """,
        (job_id,),
    ).fetchall()
    rejected = conn.execute(
        """
        SELECT m.title AS material_title, p.title AS product_title,
               GROUP_CONCAT(ac.check_name || ': ' || ac.evidence, '；') AS reasons
        FROM materials m
        JOIN products p ON p.id = m.product_id
        JOIN audit_checks ac ON ac.material_id = m.id
        WHERE m.status = 'rejected'
        GROUP BY m.id
        ORDER BY m.id
        """
    ).fetchall()
    reviews = conn.execute(
        """
        SELECT rt.id, rt.source_id, rt.reason, rt.ai_note, rt.status,
               m.title AS material_title
        FROM review_tasks rt
        LEFT JOIN materials m ON m.id = rt.source_id
        WHERE rt.source_type = 'material'
        ORDER BY rt.id
        """
    ).fetchall()

    return {
        "job": _dict(job),
        "ai_mode": ai_mode(),
        "approved_clips": [_dict(row) for row in clips],
        "rejected_materials": [_dict(row) for row in rejected],
        "review_tasks": [_dict(row) for row in reviews],
    }


def _markdown(payload: dict) -> str:
    lines = [
        "# 抖音 AI 选品剪辑引擎 - 风险报告",
        "",
        f"- 剪辑任务 ID：{payload['job']['id']}",
        f"- 输出成片：{payload['job']['output_path'] or '未生成'}",
        f"- AI 模式：{payload['ai_mode']}",
        "",
        "## 已采用片段",
    ]
    for clip in payload["approved_clips"]:
        lines.append(
            f"- {clip['position']}. {clip['product_title']} / {clip['material_title']} "
            f"({clip['start_sec']}-{clip['end_sec']}s)"
        )
    if not payload["approved_clips"]:
        lines.append("- 无")

    lines += ["", "## 已淘汰素材"]
    for item in payload["rejected_materials"]:
        lines.append(f"- {item['product_title']} / {item['material_title']}：{item['reasons']}")
    if not payload["rejected_materials"]:
        lines.append("- 无")

    lines += ["", "## 人工复核记录"]
    for item in payload["review_tasks"]:
        lines.append(
            f"- #{item['id']} {item['material_title']}：{item['reason']} "
            f"（AI 建议：{item['ai_note'] or '无'}，状态：{item['status']}）"
        )
    if not payload["review_tasks"]:
        lines.append("- 无")

    return "\n".join(lines)


def _html(payload: dict) -> str:
    rows = "".join(
        f"<tr><td>{clip['position']}</td><td>{clip['product_title']}</td>"
        f"<td>{clip['material_title']}</td><td>{clip['start_sec']}-{clip['end_sec']}s</td></tr>"
        for clip in payload["approved_clips"]
    )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>风险报告</title></head><body>
<h1>风险报告</h1>
<p>任务 ID：{payload['job']['id']} | AI 模式：{payload['ai_mode']}</p>
<p>输出成片：{payload['job']['output_path'] or '未生成'}</p>
<h2>已采用片段</h2><table border="1" cellspacing="0" cellpadding="6">
<tr><th>顺序</th><th>商品</th><th>素材</th><th>时间段</th></tr>{rows}</table>
</body></html>"""


def generate_job_report(db_path: Path | str, job_id: int) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    payload = _payload(conn, job_id)

    json_path = OUTPUT_DIR / f"report_{job_id}.json"
    md_path = OUTPUT_DIR / f"report_{job_id}.md"
    html_path = OUTPUT_DIR / f"report_{job_id}.html"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(payload), encoding="utf-8")
    html_path.write_text(_html(payload), encoding="utf-8")

    for report_type, path in (("json", json_path), ("md", md_path), ("html", html_path)):
        conn.execute(
            """
            INSERT INTO reports (product_id, job_id, report_type, output_path)
            VALUES (?, ?, ?, ?)
            """,
            (payload["job"]["product_id"], job_id, report_type, str(path)),
        )
    conn.commit()
    conn.close()
    return {"json": json_path, "md": md_path, "html": html_path}
