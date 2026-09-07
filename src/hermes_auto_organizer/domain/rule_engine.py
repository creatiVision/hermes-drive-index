"""
Modular File Organization & Cleanup Rule Engine for Hermes Auto-Organizer.

Provides modular condition evaluation for local and cloud files:
Source Folder, Timeframe / Age, Keyword / OCR Content, File Extension,
and Size, combined with AND/OR logic for automated file routing.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import fnmatch
from pathlib import Path
import re
from typing import Any, List, Optional

from hermes_auto_organizer.domain.models import FileNode


@dataclass(frozen=True, slots=True)
class RuleConditionItem:
    """A single criterion in a modular rule."""
    field: str           # "source_folder", "timeframe", "keyword", "extension", "file_size"
    operator: str        # "starts_with", "equals", "older_than_days", "newer_than_days", "contains", "is_one_of", "greater_than_mb", "less_than_mb"
    value: str
    scope: str = "both"  # For keywords: "filename", "content", "both"


def evaluate_single_condition(
    cond: dict[str, Any] | RuleConditionItem,
    node: FileNode,
    extraction_text: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Evaluates a single condition against a FileNode and optional extracted text."""
    if isinstance(cond, RuleConditionItem):
        field_type = cond.field
        op = cond.operator
        val = cond.value
        scope = cond.scope
    else:
        field_type = cond.get("field", "")
        op = cond.get("operator", "equals")
        val = str(cond.get("value", ""))
        scope = cond.get("scope", "both")

    # 1. Source folder criteria
    if field_type == "source_folder":
        folder_str = val.rstrip("/")
        src_path = node.physical_path
        rel_path = node.relative_path
        if op == "starts_with":
            return src_path.startswith(folder_str) or rel_path.startswith(folder_str)
        elif op == "equals":
            parent_dir = str(Path(src_path).parent)
            return parent_dir == folder_str or str(Path(rel_path).parent) == folder_str
        elif op == "contains":
            return folder_str in src_path or folder_str in rel_path

    # 2. Timeframe / Age criteria
    elif field_type == "timeframe":
        if now is None:
            now = datetime.now(timezone.utc)
        # Ensure node.mtime is timezone-aware
        node_mtime = node.mtime
        if node_mtime.tzinfo is None:
            node_mtime = node_mtime.replace(tzinfo=timezone.utc)
        diff_days = (now - node_mtime).total_seconds() / 86400.0
        try:
            target_days = float(val)
        except (ValueError, TypeError):
            target_days = 0.0

        if op == "older_than_days":
            return diff_days >= target_days
        elif op == "newer_than_days":
            return diff_days <= target_days

    # 3. Keyword / Text Content criteria
    elif field_type == "keyword":
        kw = val.strip().lower()
        if not kw:
            return True
        match_name = kw in node.file_name.lower()
        match_content = bool(extraction_text and (kw in extraction_text.lower()))
        if scope == "filename":
            return match_name
        elif scope == "content":
            return match_content
        else:  # both
            return match_name or match_content

    # 4. File extension criteria
    elif field_type == "extension":
        allowed = {e.strip().lower().lstrip(".") for e in val.split(",") if e.strip()}
        node_ext = (node.file_extension or Path(node.file_name).suffix).lower().lstrip(".")
        if op == "is_one_of":
            return node_ext in allowed
        elif op == "is_not_one_of":
            return node_ext not in allowed

    # 5. File size criteria
    elif field_type == "file_size":
        try:
            size_mb = float(val)
        except (ValueError, TypeError):
            size_mb = 0.0
        node_mb = node.size_bytes / (1024 * 1024)
        if op == "greater_than_mb":
            return node_mb >= size_mb
        elif op == "less_than_mb":
            return node_mb <= size_mb

    return False


def evaluate_modular_rule(
    condition_json: dict[str, Any],
    node: FileNode,
    extraction_text: Optional[str] = None,
    source_pattern: str = "*",
    now: Optional[datetime] = None,
) -> bool:
    """
    Evaluates modular rule conditions.
    Combines legacy source_pattern matching with modular condition array.
    Supports match_mode: 'all' (AND) and 'any' (OR).
    """
    # Check source pattern glob if specified
    if source_pattern and source_pattern != "*":
        if not fnmatch.fnmatch(node.relative_path, source_pattern) and not fnmatch.fnmatch(node.file_name, source_pattern):
            return False

    # Check legacy 'extensions' field if present
    if "extensions" in condition_json:
        allowed_exts = [e.lower().lstrip(".") for e in condition_json["extensions"]]
        node_ext = (node.file_extension or Path(node.file_name).suffix).lower().lstrip(".")
        if node_ext not in allowed_exts:
            return False

    # Check modular condition items
    conditions = condition_json.get("conditions")
    if not conditions:
        return True

    match_mode = str(condition_json.get("match_mode", "all")).lower()

    results = [
        evaluate_single_condition(c, node, extraction_text=extraction_text, now=now)
        for c in conditions
    ]

    if not results:
        return True

    if match_mode == "any":
        return any(results)
    else:  # "all"
        return all(results)


def resolve_destination_path(template: str, node: FileNode) -> str:
    """Interpolates variables ({year}, {month}, {day}, {file_name}, {stem}, {ext}) into destination path."""
    year_str = node.mtime.strftime("%Y")
    month_str = node.mtime.strftime("%m")
    day_str = node.mtime.strftime("%d")
    stem_str = Path(node.file_name).stem
    ext_str = node.file_extension or Path(node.file_name).suffix

    result = template
    result = result.replace("{year}", year_str)
    result = result.replace("{month}", month_str)
    result = result.replace("{day}", day_str)
    result = result.replace("{file_name}", node.file_name)
    result = result.replace("{filename}", node.file_name)
    result = result.replace("{stem}", stem_str)
    result = result.replace("{ext}", ext_str)
    result = result.replace("{extension}", ext_str)

    # If target is a directory ending with '/', append filename automatically
    if result.endswith("/"):
        result = result + node.file_name

    return result
