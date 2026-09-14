"""
Unit tests for modular rule engine and condition evaluation.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from hermes_auto_organizer.domain.models import FileNode
from hermes_auto_organizer.domain.rule_engine import (
    evaluate_modular_rule,
    evaluate_single_condition,
    resolve_destination_path,
)


def _make_node(
    file_name: str = "Rechnung_2026.pdf",
    physical_path: str = "/home/mb/Downloads/Rechnung_2026.pdf",
    days_old: int = 45,
    size_mb: float = 2.5,
) -> FileNode:
    mtime = datetime.now(timezone.utc) - timedelta(days=days_old)
    return FileNode(
        id=uuid4(),
        root_id=uuid4(),
        relative_path=file_name,
        physical_path=physical_path,
        file_name=file_name,
        size_bytes=int(size_mb * 1024 * 1024),
        mtime=mtime,
        file_extension=Path(file_name).suffix,
    )


def test_source_folder_condition():
    node = _make_node(physical_path="/home/mb/Downloads/doc.pdf")
    cond_starts = {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Downloads"}
    assert evaluate_single_condition(cond_starts, node) is True

    cond_other = {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Dokumente"}
    assert evaluate_single_condition(cond_other, node) is False


def test_timeframe_condition():
    now = datetime.now(timezone.utc)
    node_old = _make_node(days_old=40)
    cond_older = {"field": "timeframe", "operator": "older_than_days", "value": "30"}
    assert evaluate_single_condition(cond_older, node_old, now=now) is True

    cond_newer = {"field": "timeframe", "operator": "newer_than_days", "value": "10"}
    assert evaluate_single_condition(cond_newer, node_old, now=now) is False


def test_keyword_condition_filename_and_content():
    node = _make_node(file_name="Scan_001.pdf")
    # In filename: false, in OCR text: true
    cond_kw = {"field": "keyword", "operator": "contains", "value": "Rechnung", "scope": "both"}
    assert evaluate_single_condition(cond_kw, node, extraction_text=None) is False
    assert evaluate_single_condition(cond_kw, node, extraction_text="Lieferant Müller Rechnung 2026") is True

    # Filename only
    cond_name_only = {"field": "keyword", "operator": "contains", "value": "Scan", "scope": "filename"}
    assert evaluate_single_condition(cond_name_only, node) is True


def test_extension_and_size_condition():
    node = _make_node(file_name="archive.zip", size_mb=120)
    cond_ext = {"field": "extension", "operator": "is_one_of", "value": "zip,tar.gz,7z"}
    assert evaluate_single_condition(cond_ext, node) is True

    cond_size = {"field": "file_size", "operator": "greater_than_mb", "value": "100"}
    assert evaluate_single_condition(cond_size, node) is True

    cond_small = {"field": "file_size", "operator": "less_than_mb", "value": "50"}
    assert evaluate_single_condition(cond_small, node) is False


def test_modular_rule_and_or_modes():
    node = _make_node(
        file_name="Rechnung_Telekom.pdf",
        physical_path="/home/mb/Downloads/Rechnung_Telekom.pdf",
        days_old=35,
        size_mb=1.2,
    )
    rule_all = {
        "match_mode": "all",
        "conditions": [
            {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Downloads"},
            {"field": "timeframe", "operator": "older_than_days", "value": "30"},
            {"field": "keyword", "operator": "contains", "value": "Rechnung", "scope": "both"},
            {"field": "extension", "operator": "is_one_of", "value": "pdf"},
        ],
    }
    assert evaluate_modular_rule(rule_all, node) is True

    # Changing one condition in AND mode fails
    rule_all_failing = {
        "match_mode": "all",
        "conditions": [
            {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Downloads"},
            {"field": "timeframe", "operator": "older_than_days", "value": "100"},  # fails
        ],
    }
    assert evaluate_modular_rule(rule_all_failing, node) is False

    # But in OR mode it succeeds
    rule_any = {
        "match_mode": "any",
        "conditions": [
            {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Downloads"},
            {"field": "timeframe", "operator": "older_than_days", "value": "100"},
        ],
    }
    assert evaluate_modular_rule(rule_any, node) is True


def test_modular_rule_empty_conditions():
    node = _make_node(file_name="test.txt")
    assert evaluate_modular_rule({"conditions": [], "match_mode": "any"}, node) is True
    assert evaluate_modular_rule({"conditions": [], "match_mode": "all"}, node) is True
    assert evaluate_modular_rule({}, node) is True


def test_modular_rule_short_circuit_evaluation():
    node = _make_node(file_name="test.txt", physical_path="/tmp/test.txt")

    # In "all" (AND) mode, when condition 1 fails, condition 2 (with bad field/value) is never evaluated.
    rule_all_short_circuit = {
        "match_mode": "all",
        "conditions": [
            {"field": "extension", "operator": "is_one_of", "value": "pdf"},
            {"field": "keyword", "operator": "contains", "value": "nonexistent", "scope": "content"},
        ],
    }
    assert evaluate_modular_rule(rule_all_short_circuit, node) is False

    # In "any" (OR) mode, when condition 1 passes, condition 2 is short-circuited.
    rule_any_short_circuit = {
        "match_mode": "any",
        "conditions": [
            {"field": "extension", "operator": "is_one_of", "value": "pdf,txt"},
            {"field": "keyword", "operator": "contains", "value": "nonexistent", "scope": "content"},
        ],
    }
    assert evaluate_modular_rule(rule_any_short_circuit, node) is True


def test_resolve_destination_path_templates():
    node = _make_node(file_name="Rechnung_2026_09.pdf")
    year = node.mtime.strftime("%Y")
    month = node.mtime.strftime("%m")

    template_dir = "/media/privat-buero/Steuern/{year}/"
    resolved = resolve_destination_path(template_dir, node)
    assert resolved == f"/media/privat-buero/Steuern/{year}/Rechnung_2026_09.pdf"

    template_file = "/media/work-data/Archiv/{year}_{month}_{stem}{ext}"
    resolved2 = resolve_destination_path(template_file, node)
    assert resolved2 == f"/media/work-data/Archiv/{year}_{month}_Rechnung_2026_09.pdf"
