"""Command line entry points for the demo project.

Run from the project root, for example:
    python -m app.cli demo
"""

from __future__ import annotations

import argparse
import sys

from app.config import DB_PATH, MEDIA_DIR, ensure_dirs
from app.audit import audit_all
from app.db import connect, init_db, table_names
from app.editor import run_demo_edit
from app.ffmpeg import find_ffmpeg, find_ffprobe
from app.media import ensure_demo_media
from app.report import generate_job_report
from app.review import pending_tasks, resolve_task
from app.scoring import score_all
from app.seed import seed_demo

EXPECTED_TABLES = [
    "products",
    "score_details",
    "materials",
    "audit_checks",
    "review_tasks",
    "edit_jobs",
    "edit_clips",
    "reports",
]


def _cmd_init(args: argparse.Namespace) -> int:
    init_db(DB_PATH, force=args.force)
    print("[ok] database ready:", DB_PATH)
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    init_db(DB_PATH)
    counts = seed_demo(DB_PATH)
    print(f"[ok] seeded products={counts['products']} materials={counts['materials']}")
    return 0


def _cmd_media(args: argparse.Namespace) -> int:
    try:
        created = ensure_demo_media(force=args.force)
    except RuntimeError as exc:
        print("[fail] media generation failed:", exc)
        return 1
    if created:
        print(f"[ok] generated demo clips: {', '.join(created)}")
    else:
        print("[ok] demo clips already present")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    results = score_all(DB_PATH)
    for result in results:
        if result.passed:
            label = f"{result.level} / {result.total_score:.1f}"
        else:
            label = f"淘汰 / {result.total_score:.1f} / {'；'.join(result.reject_reasons)}"
        print(f"[{result.category}] {result.title} -> {label}")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    results = audit_all(DB_PATH)
    for result in results:
        checks = "；".join(f"{check.check_name}:{check.evidence}" for check in result.checks)
        if not checks:
            checks = "未命中规则"
        print(f"[{result.risk_level}/{result.status}] {result.title} -> {checks}")
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    if args.action == "list":
        tasks = pending_tasks(DB_PATH)
        if not tasks:
            print("[review] no pending tasks")
            return 0
        for task in tasks:
            print(f"#{task['id']} material={task['source_id']} reason={task['reason']}")
        return 0

    ok = resolve_task(DB_PATH, args.task_id, args.action == "approve", note=args.note or "")
    print("[ok] review updated" if ok else "[fail] task not found")
    return 0 if ok else 1


def _cmd_edit(args: argparse.Namespace) -> int:
    try:
        output = run_demo_edit(DB_PATH)
    except RuntimeError as exc:
        print("[fail] edit failed:", exc)
        return 1
    print("[ok] output:", output)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    conn = connect(DB_PATH)
    job = conn.execute("SELECT id FROM edit_jobs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if job is None:
        print("[fail] no edit job found; run `edit` first")
        return 1
    paths = generate_job_report(DB_PATH, job["id"])
    for report_type, path in paths.items():
        print(f"[ok] {report_type}: {path}")
    return 0


def _cmd_web(args: argparse.Namespace) -> int:
    from app.web import create_app

    app = create_app()
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0


def _status_block() -> list[str]:
    conn = connect(DB_PATH)
    missing = [name for name in EXPECTED_TABLES if name not in table_names(conn)]
    rows = {
        name: conn.execute(f"SELECT COUNT(*) AS n FROM {name}").fetchone()["n"]
        for name in EXPECTED_TABLES
    }
    conn.close()

    media_names = sorted(path.name for path in MEDIA_DIR.glob("*.mp4"))
    ffmpeg = find_ffmpeg()

    lines = []
    if ffmpeg:
        lines.append(f"[ok] ffmpeg: {ffmpeg}")
    else:
        lines.append("[fail] ffmpeg not found")
    if find_ffprobe():
        lines.append(f"[ok] ffprobe: {find_ffprobe()}")
    else:
        lines.append("[warn] ffprobe not found (optional for M0)")
    if missing:
        lines.append(f"[fail] missing tables: {', '.join(missing)}")
    else:
        lines.append(f"[ok] tables: {len(EXPECTED_TABLES)}/{len(EXPECTED_TABLES)}")
    lines.append(f"[ok] media clips: {len(media_names)}/{len(media_names)}")
    for name in EXPECTED_TABLES:
        lines.append(f"[ok] rows in {name}: {rows[name]}")
    lines.append("pipeline stages: import -> score(M1) -> audit(M2) -> edit(M3) -> report(M3)")
    return lines


def _cmd_demo(args: argparse.Namespace) -> int:
    ensure_dirs()
    if not args.keep_db:
        init_db(DB_PATH, force=True)
        print("[init] demo database recreated")
    init_db(DB_PATH)

    counts = seed_demo(DB_PATH)
    print(f"[seed] products={counts['products']} materials={counts['materials']}")

    try:
        created = ensure_demo_media(force=args.force_media)
    except RuntimeError as exc:
        print("[fail] media generation failed:", exc)
        return 1
    if created:
        print(f"[media] generated demo clips: {', '.join(created)}")
    else:
        print("[media] demo clips already present")

    results = score_all(DB_PATH)
    rejected = [result for result in results if not result.passed]
    print(f"[score] products={len(results)} rejected={len(rejected)}")

    audit_results = audit_all(DB_PATH)
    manual = [result for result in audit_results if result.status == "manual"]
    print(f"[audit] materials={len(audit_results)} manual_review={len(manual)}")

    try:
        output = run_demo_edit(DB_PATH)
        print(f"[edit] output={output}")
    except RuntimeError as exc:
        print(f"[edit] skipped: {exc}")

    conn = connect(DB_PATH)
    job = conn.execute("SELECT id FROM edit_jobs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if job is not None:
        paths = generate_job_report(DB_PATH, job["id"])
        print(f"[report] generated {', '.join(str(path) for path in paths.values())}")

    for line in _status_block():
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="douyin-ai-selection")
    sub = parser.add_subparsers(dest="command", required=True)

    parser_init = sub.add_parser("init-db", help="create/refresh the local database")
    parser_init.add_argument("--force", action="store_true", help="delete an existing demo.db first")
    parser_init.set_defaults(func=_cmd_init)

    parser_seed = sub.add_parser("seed", help="load built-in sample data")
    parser_seed.set_defaults(func=_cmd_seed)

    parser_media = sub.add_parser("media", help="generate synthetic demo video clips")
    parser_media.add_argument("--force", action="store_true", help="regenerate existing clips")
    parser_media.set_defaults(func=_cmd_media)

    parser_score = sub.add_parser("score", help="run explainable product scoring")
    parser_score.set_defaults(func=_cmd_score)

    parser_audit = sub.add_parser("audit", help="run material compliance audit")
    parser_audit.set_defaults(func=_cmd_audit)

    parser_review = sub.add_parser("review", help="list or resolve manual review tasks")
    parser_review.add_argument("action", choices=["list", "approve", "reject"])
    parser_review.add_argument("--task-id", type=int)
    parser_review.add_argument("--note", default="")
    parser_review.set_defaults(func=_cmd_review)

    parser_edit = sub.add_parser("edit", help="create and render an edit job from approved materials")
    parser_edit.set_defaults(func=_cmd_edit)

    parser_report = sub.add_parser("report", help="generate a report for the latest edit job")
    parser_report.set_defaults(func=_cmd_report)

    parser_web = sub.add_parser("web", help="start the local scoring web UI")
    parser_web.add_argument("--port", type=int, default=5000)
    parser_web.set_defaults(func=_cmd_web)

    parser_demo = sub.add_parser("demo", help="one-key demo")
    parser_demo.add_argument("--keep-db", action="store_true", help="do not reset demo.db")
    parser_demo.add_argument("--force-media", action="store_true", help="regenerate demo clips")
    parser_demo.set_defaults(func=_cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
