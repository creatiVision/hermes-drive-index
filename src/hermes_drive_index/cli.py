"""Command-line interface for hermes-drive-index."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from . import __version__
from .api import (
    auto_organize_downloads,
    benchmark_ocr_parameters,
    build_index,
    find_duplicates,
    flag_old_files,
    incremental_update,
    index_local_folder,
    organize_documents,
    reindex_metadata_only,
    search,
    selective_sync_plan_api,
    status,
)
from .config import load_config
from .core.organizer_workflow import (
    access_check,
    analyse_first,
    execute_on_approval,
    format_plan_presentation,
    intent_check,
    propose_plan,
    validate_approval,
)


def _config_from_args(args: argparse.Namespace):
    return load_config(
        {
            "config_path": getattr(args, "config", None),
            "root_folder_id": getattr(args, "root_folder_id", None),
            "db_path": getattr(args, "db_path", None),
            "base_dir": getattr(args, "base_dir", None),
            "ocr_enabled": getattr(args, "ocr_enabled", None),
            "ocr_image_enabled": getattr(args, "ocr_image_enabled", None),
            "ocr_pdf_args": getattr(args, "ocr_pdf_args", None),
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes Google Drive & Local Drives index and file manager")
    parser.add_argument("--version", action="version", version=f"hermes-drive-index {__version__}")
    parser.add_argument("--config", metavar="PATH", help="Path to a local TOML config file.")
    parser.add_argument("--root-folder-id", dest="root_folder_id", metavar="ID", help="Drive root folder ID override.")
    parser.add_argument("--db-path", dest="db_path", metavar="PATH", help="Index DB path override.")
    parser.add_argument("--base-dir", dest="base_dir", metavar="DIR", help="Base directory override.")
    parser.add_argument("--ocr", dest="ocr_enabled", action="store_true", default=None, help="Enable optional OCR for scanned PDFs.")
    parser.add_argument("--no-ocr", dest="ocr_enabled", action="store_false", help="Disable OCR even if config/env enables it.")
    parser.add_argument("--ocr-pdf-arg", dest="ocr_pdf_args", action="append", metavar="ARG", help="Override OCRmyPDF preprocessing/config args.")
    parser.add_argument("--ocr-image", dest="ocr_image_enabled", action="store_true", default=None, help="Enable optional OCR indexing for supported images.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Core indexing commands
    build_p = sub.add_parser("build")
    build_p.add_argument("--mode", choices=["weekly_full", "full", "incremental", "incremental_manifest"], default="weekly_full")
    build_p.add_argument("--json", action="store_true", help="Build output in JSON format.")

    update_p = sub.add_parser("update")
    update_p.add_argument("--mode", choices=["incremental", "incremental_manifest", "reindex_metadata_only"], default="incremental_manifest")
    update_p.add_argument("--json", action="store_true", help="Update output in JSON format.")

    incremental_p = sub.add_parser("incremental")
    incremental_p.add_argument("--json", action="store_true", help="Incremental output in JSON format.")

    status_p = sub.add_parser("status")
    status_p.add_argument("--json", action="store_true", help="Status output in JSON format.")

    doctor_p = sub.add_parser("doctor")
    doctor_p.add_argument("--json", action="store_true", help="Doctor output in JSON format.")

    bench_p = sub.add_parser("benchmark-ocr", help="Run read-only aggregate OCR parameter benchmark.")
    bench_p.add_argument("--json", action="store_true")
    bench_p.add_argument("--mode", dest="modes", action="append", metavar="MODE")
    bench_p.add_argument("--limit", type=int, metavar="N")
    bench_p.add_argument("--golden", metavar="PATH")

    sp = sub.add_parser("search")
    sp.add_argument("query", metavar="QUERY")
    sp.add_argument("--top", type=int, default=8, metavar="N")
    sp.add_argument("--json", action="store_true")

    # Local drive and cleanup subcommands
    dupes_p = sub.add_parser("duplicates", help="Scan for exact duplicates, near duplicates, and version variants.")
    dupes_p.add_argument("folder", metavar="FOLDER")
    dupes_p.add_argument("--json", action="store_true", default=True)

    old_p = sub.add_parser("cleanup-old", help="Analyze old files and generate tiered cleanup inventory.")
    old_p.add_argument("folder", metavar="FOLDER")
    old_p.add_argument("--days", type=int, default=90, metavar="DAYS")
    old_p.add_argument("--json", action="store_true", default=True)

    dl_p = sub.add_parser("organize-downloads", help="Plan sorting flat downloads folder by type and date.")
    dl_p.add_argument("folder", metavar="FOLDER")
    dl_p.add_argument("--no-date", dest="by_date", action="store_false", default=True)
    dl_p.add_argument("--json", action="store_true", default=True)

    doc_p = sub.add_parser("organize-documents", help="Plan intelligent 4-6 folder structure for documents.")
    doc_p.add_argument("folder", metavar="FOLDER")
    doc_p.add_argument("--json", action="store_true", default=True)

    # SKILL.md workflow commands
    ana_p = sub.add_parser("organize-analyze", help="Analyze folder: check access, nesting, patterns, duplicates.")
    ana_p.add_argument("folder", metavar="FOLDER")
    ana_p.add_argument("--json", action="store_true")

    plan_p = sub.add_parser("organize-plan", help="Propose reorganization plan with before-to-after mapping.")
    plan_p.add_argument("folder", metavar="FOLDER")
    plan_p.add_argument("--mode", choices=["downloads", "documents"], default="downloads")
    plan_p.add_argument("--json", action="store_true")

    exec_p = sub.add_parser("organize-execute", help="Execute reorganization plan upon explicit approval.")
    exec_p.add_argument("folder", metavar="FOLDER")
    exec_p.add_argument("--mode", choices=["downloads", "documents"], default="downloads")
    exec_p.add_argument("--approval", default="", metavar="STR", help="User approval string ('approve' or 'go ahead').")
    exec_p.add_argument("--dry-run", action="store_true", default=False)
    exec_p.add_argument("--json", action="store_true")

    # Local indexing & selective sync
    idx_p = sub.add_parser("index-local", help="Index a local directory directly into the SQLite index.")
    idx_p.add_argument("folder", metavar="FOLDER")
    idx_p.add_argument("--json", action="store_true", default=True)

    sync_p = sub.add_parser("sync-plan", help="Plan selective sync between designated local and Drive folders.")
    sync_p.add_argument("--mapping", default=None, metavar="NAME")
    sync_p.add_argument("--json", action="store_true", default=True)

    args = parser.parse_args(argv)
    cfg = _config_from_args(args)

    if args.cmd == "build":
        result = incremental_update(cfg) if args.mode in {"incremental", "incremental_manifest"} else build_index(cfg)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.cmd in {"update", "incremental"}:
        result = reindex_metadata_only(cfg) if args.cmd == "update" and args.mode == "reindex_metadata_only" else incremental_update(cfg)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "status":
        print(json.dumps(status(cfg), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "doctor":
        import importlib.metadata as metadata
        eps = [str(e) for e in metadata.entry_points(group="hermes_agent.plugins") if "hermes_drive_index" in str(e)]
        print(json.dumps({"package": "hermes-drive-index", "version": __version__, "plugin_entry_points": eps, "status": status(cfg)}, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "benchmark-ocr":
        result = benchmark_ocr_parameters(cfg, modes=args.modes, limit=args.limit, golden_path=args.golden)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "search":
        result = search(args.query, args.top, cfg)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Query: {result['query']} ({result['latency_ms']} ms)")
            for i, row in enumerate(result["results"], 1):
                print(f"\n{i}. {row['name']}\n   {row['path']}\n   {row.get('web_view_link')}\n   {row['snippet']}")
        return 0
    if args.cmd == "duplicates":
        res = find_duplicates(args.folder)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "cleanup-old":
        res = flag_old_files(args.folder, days_threshold=args.days)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "organize-downloads":
        res = auto_organize_downloads(args.folder, by_date=args.by_date)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "organize-documents":
        res = organize_documents(args.folder)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "organize-analyze":
        acc = access_check(args.folder)
        if not acc["accessible"]:
            print(json.dumps(acc, indent=2))
            return 1
        res = analyse_first(args.folder)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(res["markdown_summary"])
        return 0
    if args.cmd == "organize-plan":
        plan = propose_plan(args.folder, organize_mode=args.mode)
        if args.json:
            print(json.dumps(asdict(plan), indent=2, ensure_ascii=False))
        else:
            print(format_plan_presentation(plan))
        return 0
    if args.cmd == "organize-execute":
        plan = propose_plan(args.folder, organize_mode=args.mode)
        if not args.dry_run and not validate_approval(args.approval):
            print(json.dumps({
                "success": False,
                "error": "Explicit approval not provided. Supply --approval 'approve' or use --dry-run."
            }, indent=2))
            return 1
        res = execute_on_approval(plan, dry_run=args.dry_run)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "index-local":
        res = index_local_folder(args.folder, cfg)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "sync-plan":
        res = selective_sync_plan_api(args.mapping, cfg)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
