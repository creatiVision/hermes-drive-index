"""Thin Hermes tool wrappers.

Handlers are deliberately stateless: they parse args, call package API functions,
and return JSON strings. This avoids long-lived wrapper defaults drifting from the
core implementation.

Adapter contract (stable, relied on by Hermes):

* Every handler returns a JSON **string** with a top-level ``success`` bool and a
  ``package_version`` field, on both the success and error paths. Errors never
  raise out of the handler — they are reported as ``{"success": false, "error": ...}``.
* ``check_drive_index_requirements`` intentionally returns ``True`` so the tools
  stay discoverable; any real failure surfaces as a structured error at call time.
* ``drive_index_search`` clamps ``top_k`` to the range 1–25.
* ``drive_index_update`` is long-running and is the same code path the CLI uses,
  so it is safe to drive from a cron wrapper (``hermes-drive-index update``).
* File cleanup and organization tools follow strict safety guidelines (explicit
  approval, dry-run by default, safe trash).
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from hermes_drive_index import __version__
from hermes_drive_index.api import (
    OrganizerPlan,
    access_check,
    analyse_first,
    auto_organize_downloads,
    build_index,
    execute_on_approval,
    find_duplicates,
    flag_old_files,
    format_plan_presentation,
    incremental_update,
    index_local_folder,
    intent_check,
    organize_documents,
    propose_plan,
    reindex_metadata_only,
    search,
    selective_sync_plan_api,
    status,
    validate_approval,
)


def check_drive_index_requirements() -> bool:
    try:
        status()
        return True
    except Exception:
        # Keep available if package imports; individual handlers return structured errors.
        return True


def drive_index_search(query: str, top_k: int = 8) -> str:
    if not query or not query.strip():
        return json.dumps({"success": False, "error": "query is required"})
    try:
        result = search(query=query, top_k=max(1, min(int(top_k or 8), 25)))
        return json.dumps({"success": True, "package_version": __version__, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def drive_index_status() -> str:
    try:
        result = status()
        return json.dumps({"success": True, "package_version": __version__, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def drive_index_update(mode: str = "incremental_manifest") -> str:
    try:
        normalized = (mode or "incremental_manifest").strip().lower()
        if normalized in {"incremental", "incremental_manifest"}:
            result = incremental_update()
        elif normalized == "reindex_metadata_only":
            result = reindex_metadata_only()
        else:
            result = build_index()
        result["requested_mode"] = mode
        return json.dumps({"success": True, "package_version": __version__, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "requested_mode": mode, "package_version": __version__}, ensure_ascii=False)


def file_organizer_analyze_handler(folder_path: str, user_intent: str = "organize") -> str:
    try:
        intent = intent_check(user_intent, folder_path)
        if not intent.get("proceed"):
            return json.dumps({"success": False, "message": intent["message"], "package_version": __version__}, ensure_ascii=False)
        access = access_check(folder_path)
        if not access.get("accessible"):
            return json.dumps({"success": False, "access_check": access, "package_version": __version__}, ensure_ascii=False)
        analysis = analyse_first(folder_path)
        return json.dumps({"success": True, "package_version": __version__, **analysis}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def file_organizer_plan_handler(folder_path: str, organize_mode: str = "downloads") -> str:
    try:
        plan = propose_plan(folder_path, organize_mode=organize_mode)
        formatted = format_plan_presentation(plan)
        return json.dumps({
            "success": True,
            "package_version": __version__,
            "plan": asdict(plan),
            "presentation": formatted,
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def file_organizer_execute_handler(plan: dict | None, approval: str, dry_run: bool = False) -> str:
    try:
        if not plan:
            return json.dumps({"success": False, "error": "plan is required", "package_version": __version__})
        if not dry_run and not validate_approval(approval):
            return json.dumps({
                "success": False,
                "approved": False,
                "error": "Explicit approval not detected. Please reply 'approve' or 'go ahead' to proceed, or describe what to change.",
                "package_version": __version__,
            })
        from hermes_drive_index.core.organizer_workflow import OrganizerAction
        actions = [OrganizerAction(**a) for a in plan.get("actions", [])]
        p = OrganizerPlan(
            folder_path=plan.get("folder_path", ""),
            actions=actions,
            dry_run=dry_run,
        )
        res = execute_on_approval(p, dry_run=dry_run)
        return json.dumps({"success": res.get("success", False), "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def duplicate_detector_handler(folder_path: str) -> str:
    try:
        res = find_duplicates(folder_path)
        return json.dumps({"success": True, "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def old_file_cleanup_handler(folder_path: str, days_threshold: int = 90) -> str:
    try:
        res = flag_old_files(folder_path, days_threshold=int(days_threshold or 90))
        return json.dumps({"success": True, "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def auto_organize_downloads_handler(folder_path: str, by_date: bool = True) -> str:
    try:
        res = auto_organize_downloads(folder_path, by_date=bool(by_date))
        return json.dumps({"success": True, "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def intelligent_document_organizer_handler(folder_path: str) -> str:
    try:
        res = organize_documents(folder_path)
        return json.dumps({"success": True, "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def local_drive_index_handler(folder_path: str) -> str:
    try:
        res = index_local_folder(folder_path)
        return json.dumps({"success": True, "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


def selective_sync_plan_handler(mapping_name: str = "") -> str:
    try:
        res = selective_sync_plan_api(mapping_name or None)
        return json.dumps({"success": True, "package_version": __version__, **res}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": repr(exc), "package_version": __version__}, ensure_ascii=False)


# Schemas
DRIVE_INDEX_SEARCH_SCHEMA: dict[str, Any] = {
    "name": "drive_index_search",
    "description": "Search the configured local Google Drive document index. Returns ranked snippets and Drive links.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "top_k": {"type": "integer", "description": "Maximum results, 1-25. Default 8.", "default": 8},
        },
        "required": ["query"],
    },
}

DRIVE_INDEX_STATUS_SCHEMA: dict[str, Any] = {
    "name": "drive_index_status",
    "description": "Check whether the configured local Google Drive index exists and view last run metrics.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

DRIVE_INDEX_UPDATE_SCHEMA: dict[str, Any] = {
    "name": "drive_index_update",
    "description": "Update the configured local Google Drive document index. Incremental manifest mode is the safe default.",
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "description": "Update mode: incremental/incremental_manifest, reindex_metadata_only, or weekly_full/full.", "default": "incremental_manifest"}
        },
        "required": [],
    },
}

FILE_ORGANIZER_ANALYZE_SCHEMA: dict[str, Any] = {
    "name": "file_organizer_analyze",
    "description": "Examine a local folder: checks access, counts files, nesting, naming patterns, duplicates, and orphan files.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to folder to analyze."},
            "user_intent": {"type": "string", "description": "What user wants to achieve.", "default": "organize"},
        },
        "required": ["folder_path"],
    },
}

FILE_ORGANIZER_PLAN_SCHEMA: dict[str, Any] = {
    "name": "file_organizer_plan",
    "description": "Propose concrete before-to-after mapping for renames/moves, folders to create, and files to trash.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to folder."},
            "organize_mode": {"type": "string", "enum": ["downloads", "documents"], "default": "downloads"},
        },
        "required": ["folder_path"],
    },
}

FILE_ORGANIZER_EXECUTE_SCHEMA: dict[str, Any] = {
    "name": "file_organizer_execute",
    "description": "Execute approved file reorganization plan (create folders -> move -> rename -> trash) with strict safety.",
    "parameters": {
        "type": "object",
        "properties": {
            "plan": {"type": "object", "description": "Plan object returned from file_organizer_plan."},
            "approval": {"type": "string", "description": "User's approval text (e.g. 'approve', 'go ahead')."},
            "dry_run": {"type": "boolean", "description": "Perform dry run without touching files.", "default": False},
        },
        "required": ["plan", "approval"],
    },
}

DUPLICATE_FILE_DETECTOR_SCHEMA: dict[str, Any] = {
    "name": "duplicate_file_detector",
    "description": "Detect exact byte duplicates, near-duplicates, and version variants (_v2, _final), with keep/delete suggestions.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to folder to scan."},
        },
        "required": ["folder_path"],
    },
}

OLD_FILE_CLEANUP_SCHEMA: dict[str, Any] = {
    "name": "old_file_cleanup",
    "description": "Flag old and safely deletable files in tiered inventory: safe trash (temp/installers), review needed, active.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to folder to scan."},
            "days_threshold": {"type": "integer", "description": "Inactivity threshold in days. Default 90.", "default": 90},
        },
        "required": ["folder_path"],
    },
}

AUTO_ORGANIZE_DOWNLOADS_SCHEMA: dict[str, Any] = {
    "name": "auto_organize_downloads",
    "description": "Sort flat Downloads folder into subfolders by file type and year, flagging duplicates.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to downloads folder."},
            "by_date": {"type": "boolean", "description": "Subdivide types by year.", "default": True},
        },
        "required": ["folder_path"],
    },
}

INTELLIGENT_DOCUMENT_ORGANIZER_SCHEMA: dict[str, Any] = {
    "name": "intelligent_document_organizer",
    "description": "Propose clean 4-6 top-level folder hierarchy (Projects, Finances, Personal, Reference, Archive) for documents.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to documents folder."},
        },
        "required": ["folder_path"],
    },
}

LOCAL_DRIVE_INDEX_SCHEMA: dict[str, Any] = {
    "name": "local_drive_index",
    "description": "Index a specified local folder directly into the SQLite search index for unified search.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Path to local folder to index."},
        },
        "required": ["folder_path"],
    },
}

SELECTIVE_SYNC_PLAN_SCHEMA: dict[str, Any] = {
    "name": "selective_sync_plan",
    "description": "Plan selective synchronization between designated local folders and Google Drive.",
    "parameters": {
        "type": "object",
        "properties": {
            "mapping_name": {"type": "string", "description": "Optional name of mapping to plan."},
        },
        "required": [],
    },
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "drive_index_search",
        "toolset": "drive_index",
        "schema": DRIVE_INDEX_SEARCH_SCHEMA,
        "handler": lambda args, **kw: drive_index_search(query=args.get("query", ""), top_k=args.get("top_k", 8)),
        "check_fn": check_drive_index_requirements,
        "emoji": "🗂️",
    },
    {
        "name": "drive_index_status",
        "toolset": "drive_index",
        "schema": DRIVE_INDEX_STATUS_SCHEMA,
        "handler": lambda args, **kw: drive_index_status(),
        "check_fn": check_drive_index_requirements,
        "emoji": "🗂️",
    },
    {
        "name": "drive_index_update",
        "toolset": "drive_index",
        "schema": DRIVE_INDEX_UPDATE_SCHEMA,
        "handler": lambda args, **kw: drive_index_update(mode=args.get("mode", "incremental_manifest")),
        "check_fn": check_drive_index_requirements,
        "emoji": "🗂️",
        "max_result_size_chars": 20000,
    },
    {
        "name": "file_organizer_analyze",
        "toolset": "file_organizer",
        "schema": FILE_ORGANIZER_ANALYZE_SCHEMA,
        "handler": lambda args, **kw: file_organizer_analyze_handler(folder_path=args.get("folder_path", ""), user_intent=args.get("user_intent", "organize")),
        "check_fn": check_drive_index_requirements,
        "emoji": "🔍",
    },
    {
        "name": "file_organizer_plan",
        "toolset": "file_organizer",
        "schema": FILE_ORGANIZER_PLAN_SCHEMA,
        "handler": lambda args, **kw: file_organizer_plan_handler(folder_path=args.get("folder_path", ""), organize_mode=args.get("organize_mode", "downloads")),
        "check_fn": check_drive_index_requirements,
        "emoji": "📋",
    },
    {
        "name": "file_organizer_execute",
        "toolset": "file_organizer",
        "schema": FILE_ORGANIZER_EXECUTE_SCHEMA,
        "handler": lambda args, **kw: file_organizer_execute_handler(plan=args.get("plan"), approval=args.get("approval", ""), dry_run=args.get("dry_run", False)),
        "check_fn": check_drive_index_requirements,
        "emoji": "🚀",
    },
    {
        "name": "duplicate_file_detector",
        "toolset": "file_cleaner",
        "schema": DUPLICATE_FILE_DETECTOR_SCHEMA,
        "handler": lambda args, **kw: duplicate_detector_handler(folder_path=args.get("folder_path", "")),
        "check_fn": check_drive_index_requirements,
        "emoji": "👥",
    },
    {
        "name": "old_file_cleanup",
        "toolset": "file_cleaner",
        "schema": OLD_FILE_CLEANUP_SCHEMA,
        "handler": lambda args, **kw: old_file_cleanup_handler(folder_path=args.get("folder_path", ""), days_threshold=args.get("days_threshold", 90)),
        "check_fn": check_drive_index_requirements,
        "emoji": "🧹",
    },
    {
        "name": "auto_organize_downloads",
        "toolset": "file_cleaner",
        "schema": AUTO_ORGANIZE_DOWNLOADS_SCHEMA,
        "handler": lambda args, **kw: auto_organize_downloads_handler(folder_path=args.get("folder_path", ""), by_date=args.get("by_date", True)),
        "check_fn": check_drive_index_requirements,
        "emoji": "📥",
    },
    {
        "name": "intelligent_document_organizer",
        "toolset": "file_cleaner",
        "schema": INTELLIGENT_DOCUMENT_ORGANIZER_SCHEMA,
        "handler": lambda args, **kw: intelligent_document_organizer_handler(folder_path=args.get("folder_path", "")),
        "check_fn": check_drive_index_requirements,
        "emoji": "📑",
    },
    {
        "name": "local_drive_index",
        "toolset": "local_drive",
        "schema": LOCAL_DRIVE_INDEX_SCHEMA,
        "handler": lambda args, **kw: local_drive_index_handler(folder_path=args.get("folder_path", "")),
        "check_fn": check_drive_index_requirements,
        "emoji": "💾",
    },
    {
        "name": "selective_sync_plan",
        "toolset": "selective_sync",
        "schema": SELECTIVE_SYNC_PLAN_SCHEMA,
        "handler": lambda args, **kw: selective_sync_plan_handler(mapping_name=args.get("mapping_name", "")),
        "check_fn": check_drive_index_requirements,
        "emoji": "🔄",
    },
]


def plugin_context_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {key: spec[key] for key in ("name", "toolset", "schema", "handler", "check_fn", "emoji")}


def register_tools(registry, **_: Any) -> None:
    for spec in TOOL_SPECS:
        registry.register(**spec)
