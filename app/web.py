"""Minimal Flask web UI for the product scoring page."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, redirect, render_template, request, send_from_directory, url_for

from app.ai import ai_mode
from app.config import DB_PATH
from app.db import connect
from app.editor import run_demo_edit
from app.i18n import translate
from app.report import OUTPUT_DIR, generate_job_report
from app.review import resolve_task


def _level(status: str, total_score: float) -> str:
    if status == "rejected":
        return "淘汰"
    if total_score >= 85:
        return "S"
    if total_score >= 70:
        return "A"
    if total_score >= 50:
        return "B"
    return "C"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.context_processor
    def inject_i18n():
        lang = request.args.get("lang", "zh")
        if lang not in ("zh", "en"):
            lang = "zh"
        return {"lang": lang, "t": lambda key: translate(lang, key)}

    @app.route("/")
    def dashboard():
        conn = connect()
        counts = {}
        for table in ["products", "materials", "audit_checks", "edit_jobs", "reports"]:
            counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM review_tasks WHERE status = 'pending'"
        ).fetchone()["n"]
        material_status = {
            row["status"]: row["n"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS n FROM materials GROUP BY status"
            ).fetchall()
        }
        approved = material_status.get("approved", 0)
        audited = sum(material_status.values())
        safe_rate = round(approved * 100 / audited, 1) if audited else 0
        queue = conn.execute(
            """
            SELECT m.id, m.title, m.status, p.title AS product_title,
                   COALESCE(MAX(a.risk_level), 'low') AS risk_level
            FROM materials m
            JOIN products p ON p.id = m.product_id
            LEFT JOIN audit_checks a ON a.material_id = m.id
            WHERE m.status IN ('manual', 'rejected', 'approved')
            GROUP BY m.id
            ORDER BY CASE m.status WHEN 'manual' THEN 0 WHEN 'rejected' THEN 1 ELSE 2 END, m.id
            LIMIT 3
            """
        ).fetchall()
        risk_rows = conn.execute(
            "SELECT risk_level, COUNT(*) AS n FROM audit_checks GROUP BY risk_level"
        ).fetchall()
        risk_counts = {row["risk_level"]: row["n"] for row in risk_rows}
        conn.close()
        thumbnails = [
            "images/product-cleaning-brush.png",
            "images/product-storage-box.png",
            "images/product-teeth-device.png",
        ]
        queue_items = [
            {
                "id": row["id"],
                "title": row["product_title"],
                "material_title": row["title"],
                "status": row["status"],
                "risk_level": row["risk_level"],
                "thumbnail": thumbnails[index % len(thumbnails)],
            }
            for index, row in enumerate(queue)
        ]
        return render_template(
            "dashboard.html",
            counts=counts,
            pending=pending,
            ai_mode=ai_mode(),
            safe_rate=safe_rate,
            intercepted=material_status.get("rejected", 0),
            queue_items=queue_items,
            risk_counts=risk_counts,
        )

    @app.route("/products")
    def products():
        conn = connect()
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.category, p.price, p.status, p.remark,
                   COALESCE(
                       SUM(
                           CASE WHEN sd.dimension <> '硬性淘汰'
                                THEN sd.score * sd.weight / 100.0
                                ELSE 0 END
                       ),
                       0
                   ) AS total_score,
                   (
                       SELECT GROUP_CONCAT(sd2.reason, '；')
                       FROM score_details sd2
                       WHERE sd2.product_id = p.id
                         AND sd2.dimension = '硬性淘汰'
                   ) AS reject_reason
            FROM products p
            LEFT JOIN score_details sd ON sd.product_id = p.id
            GROUP BY p.id
            ORDER BY p.id
            """
        ).fetchall()
        conn.close()

        items = []
        for row in rows:
            total_score = round(row["total_score"], 1)
            items.append(
                {
                    "title": row["title"],
                    "category": row["category"],
                    "price": "-" if row["price"] is None else f"{row['price']:.1f}",
                    "total_score": total_score,
                    "level": _level(row["status"], total_score),
                    "status_label": "已淘汰" if row["status"] == "rejected" else "已评分",
                    "status_class": "rejected" if row["status"] == "rejected" else "scored",
                    "reason": row["reject_reason"] or row["remark"] or "",
                }
            )

        return render_template("products.html", products=items)

    @app.route("/materials")
    def materials():
        conn = connect()
        material_rows = conn.execute(
            """
            SELECT m.id, m.title, m.status, p.title AS product_title
            FROM materials m
            JOIN products p ON p.id = m.product_id
            ORDER BY m.id
            """
        ).fetchall()
        check_rows = conn.execute(
            """
            SELECT material_id, check_name, evidence, risk_level, decision
            FROM audit_checks
            ORDER BY material_id, id
            """
        ).fetchall()
        pending_rows = conn.execute(
            """
            SELECT source_id
            FROM review_tasks
            WHERE status = 'pending' AND source_type = 'material'
            """
        ).fetchall()
        conn.close()

        pending_ids = {row["source_id"] for row in pending_rows}
        checks_by_material: dict[int, list[dict]] = {}
        for row in check_rows:
            checks_by_material.setdefault(row["material_id"], []).append(
                {
                    "check_name": row["check_name"],
                    "evidence": row["evidence"],
                    "risk_level": row["risk_level"],
                    "decision": row["decision"],
                }
            )

        risk_order = {"low": 0, "medium": 1, "high": 2}
        items = []
        for row in material_rows:
            checks = checks_by_material.get(row["id"], [])
            risk_level = max(
                (check["risk_level"] for check in checks),
                key=lambda value: risk_order[value],
                default="low",
            )
            items.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "product_title": row["product_title"],
                    "status": row["status"],
                    "status_label": {
                        "pending": "未审核",
                        "approved": "通过",
                        "rejected": "淘汰",
                        "manual": "待人工复核",
                    }.get(row["status"], row["status"]),
                    "risk_level": risk_level,
                    "risk_label": {"low": "低", "medium": "中", "high": "高"}[risk_level],
                    "checks": checks,
                    "can_review": row["status"] == "manual" and row["id"] in pending_ids,
                }
            )

        return render_template("materials.html", materials=items)

    @app.route("/materials/<int:material_id>/resolve", methods=["POST"])
    def resolve_material(material_id: int):
        approved = request.form.get("decision") == "approve"
        conn = connect()
        task = conn.execute(
            """
            SELECT id
            FROM review_tasks
            WHERE status = 'pending' AND source_type = 'material' AND source_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (material_id,),
        ).fetchone()
        conn.close()
        if task is not None:
            resolve_task(DB_PATH, task["id"], approved, note="web review")
        return redirect(url_for("materials", lang=request.args.get("lang", "zh")))

    @app.route("/jobs")
    def jobs():
        conn = connect()
        rows = conn.execute("SELECT * FROM edit_jobs ORDER BY id DESC").fetchall()
        conn.close()
        return render_template("jobs.html", jobs=rows)

    @app.route("/jobs/run", methods=["POST"])
    def run_job():
        try:
            run_demo_edit(DB_PATH)
            conn = connect()
            job = conn.execute("SELECT id FROM edit_jobs ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()
            if job is not None:
                generate_job_report(DB_PATH, job["id"])
        except RuntimeError:
            pass
        return redirect(url_for("jobs", lang=request.args.get("lang", "zh")))

    @app.route("/reports")
    def reports():
        conn = connect()
        rows = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
        conn.close()
        return render_template("reports.html", reports=rows)

    @app.route("/reports/<int:report_id>/download")
    def download_report(report_id: int):
        conn = connect()
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        conn.close()
        if row is None:
            return "not found", 404
        path = Path(row["output_path"])
        return send_from_directory(path.parent, path.name, as_attachment=True)

    return app
