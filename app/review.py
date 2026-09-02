"""Human review queue helpers shared by the CLI and web UI."""

from __future__ import annotations

from pathlib import Path

from app.db import connect


def pending_tasks(db_path: Path | str) -> list:
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT * FROM review_tasks WHERE status = 'pending' ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def resolve_task(
    db_path: Path | str,
    task_id: int,
    approved: bool,
    note: str = "",
) -> bool:
    conn = connect(db_path)
    task = conn.execute("SELECT * FROM review_tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        conn.close()
        return False

    new_status = "approved" if approved else "rejected"
    conn.execute(
        """
        UPDATE review_tasks
        SET status = ?, reviewed_at = datetime('now', 'localtime'), note = ?
        WHERE id = ?
        """,
        (new_status, note, task_id),
    )

    if task["source_type"] == "material":
        material_status = "approved" if approved else "rejected"
        conn.execute(
            "UPDATE materials SET status = ? WHERE id = ?",
            (material_status, task["source_id"]),
        )

    conn.commit()
    conn.close()
    return True
