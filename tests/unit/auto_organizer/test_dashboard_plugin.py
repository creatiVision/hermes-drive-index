"""
Unit tests for Hermes Dashboard Plugin Manifest and API endpoints.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from hermes_auto_organizer.dashboard.plugin_api import (
    router,
    health_check,
    get_stats,
    list_roots,
    dry_run_simulation,
    _DRY_RUN_CACHE,
)
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/plugins/auto-organizer")
client = TestClient(app)


def test_manifest_structure():
    manifest_path = Path(__file__).parents[3] / "src" / "hermes_auto_organizer" / "dashboard" / "manifest.json"
    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["name"] == "auto-organizer"
    assert data["label"] == "Auto Organizer"
    assert data["icon"] == "FolderTree"
    assert data["tab"]["path"] == "/organizer"
    assert data["entry"] == "dist/index.js"
    assert data["css"] == "dist/style.css"
    assert data["api"] == "plugin_api.py"

    dist_js = manifest_path.parent / data["entry"]
    dist_css = manifest_path.parent / data["css"]
    assert dist_js.exists()
    assert dist_css.exists()


def test_health_check_disconnected():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["plugin"] == "auto-organizer"
        assert data["database_connected"] is False


def test_health_check_connected():
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"c": 8}
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["database_connected"] is True
        assert data["table_count"] == 8


def test_stats_endpoint():
    mock_conn = AsyncMock()
    mock_conn.fetchrow.side_effect = [
        {"count": 142, "size": 104857600},  # file_nodes
        {"count": 4},                        # storage_roots
        {"count": 3},                        # anomalies
        {"count": 5},                        # rules
        {"count": 2},                        # execution_log
    ]
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total_files"] == 142
        assert data["total_size_mb"] == 100.0
        assert data["open_anomalies"] == 3
        assert data["active_rules"] == 5


def test_dry_run_simulation_endpoint():
    from datetime import datetime, timezone
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = [
        [
            {
                "id": uuid4(),
                "rule_name": "Invoices",
                "source_pattern": "*",
                "condition_json": json.dumps({
                    "match_mode": "all",
                    "conditions": [{"field": "keyword", "operator": "contains", "value": "invoice"}]
                }),
                "target_path_template": "/media/privat-data/Archiv/{year}/",
                "state": "USER_APPROVED",
            }
        ],
        [
            {
                "id": uuid4(),
                "root_id": uuid4(),
                "relative_path": "invoice.pdf",
                "physical_path": "/home/mb/Downloads/invoice.pdf",
                "file_name": "invoice.pdf",
                "size_bytes": 2048,
                "mtime": datetime.now(timezone.utc),
                "file_extension": ".pdf",
                "content_sha256": "hash123",
                "summary_text": "invoice text",
            }
        ],
    ]
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        res = client.post("/api/plugins/auto-organizer/dry-run", json={"max_items": 10})
        assert res.status_code == 200
        data = res.json()
        assert data["actions_count"] == 1
        assert data["actions"][0]["file_name"] == "invoice.pdf"
        assert data["batch_id"].startswith("dry_")


def test_toggle_rule_endpoint():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "UPDATE 1"
    test_uuid = str(uuid4())
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        res = client.post("/api/plugins/auto-organizer/rules/toggle", json={"rule_id": test_uuid, "active": True})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["state"] == "USER_APPROVED"


def test_create_modular_rule_endpoint():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "INSERT 1"
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        payload = {
            "name": "Rechnungen archivieren",
            "description": "Auto move PDFs",
            "match_mode": "all",
            "conditions": [
                {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Downloads"},
                {"field": "keyword", "operator": "contains", "value": "Rechnung", "scope": "both"}
            ],
            "target_path_template": "/media/privat-buero/Steuern/{year}/",
            "priority": 10,
            "state": "USER_APPROVED"
        }
        res = client.post("/api/plugins/auto-organizer/rules", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["name"] == "Rechnungen archivieren"


def test_test_modular_rule_endpoint():
    from datetime import datetime, timezone
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": uuid4(),
            "root_id": uuid4(),
            "relative_path": "Rechnung_2026.pdf",
            "physical_path": "/home/mb/Downloads/Rechnung_2026.pdf",
            "file_name": "Rechnung_2026.pdf",
            "size_bytes": 10240,
            "mtime": datetime.now(timezone.utc),
            "file_extension": ".pdf",
            "content_sha256": "abc123",
            "summary_text": "Rechnung für Dienstleistungen",
        }
    ]
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        payload = {
            "match_mode": "all",
            "conditions": [
                {"field": "source_folder", "operator": "starts_with", "value": "/home/mb/Downloads"},
                {"field": "keyword", "operator": "contains", "value": "Rechnung", "scope": "both"}
            ],
            "target_path_template": "/media/privat-buero/Steuern/{year}/",
            "max_items": 10
        }
        res = client.post("/api/plugins/auto-organizer/rules/test", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["matches_count"] == 1
        assert data["sample_matches"][0]["file_name"] == "Rechnung_2026.pdf"


def test_delete_rule_endpoint():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "DELETE 1"
    test_uuid = str(uuid4())
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        res = client.delete(f"/api/plugins/auto-organizer/rules/{test_uuid}")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["rule_id"] == test_uuid


def test_get_taxonomy_tree_endpoint():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/taxonomy")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["total_nodes"] >= 5
        assert len(data["tree"]) >= 5
        assert data["tree"][0]["name"] == "10_PrivatBüro / Steuern & Finanzen"


def test_approve_taxonomy_endpoint():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.post("/api/plugins/auto-organizer/taxonomy/approve", json={"approve_all": True})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["system_approved"] is True
        assert data["approved_count"] >= 5


def test_sync_mappings_list():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/sync/mappings")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["total"] >= 3
        mappings = data["mappings"]
        assert any(m["name"] == "PrivatBüro Dokumente" for m in mappings)
        assert any(m["name"] == "Work & Projekte" for m in mappings)
        # Check mount check enrichment
        first = mappings[0]
        assert "mount_check" in first


def test_save_sync_mapping():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        payload = {
            "name": "Test Sync Pair",
            "drive_folder_path": "/TestDrive",
            "local_path": "/media/test-local",
            "direction": "bidirectional",
            "include_patterns": ["*.pdf"],
            "exclude_patterns": ["*.tmp"],
        }
        res = client.post("/api/plugins/auto-organizer/sync/mappings", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["mapping"]["name"] == "Test Sync Pair"
        assert data["mapping"]["drive_folder_path"] == "/TestDrive"
        assert "mount_check" in data["mapping"]


def test_toggle_and_plan_sync_mapping():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        # Toggle
        res = client.post("/api/plugins/auto-organizer/sync/mappings/toggle", json={
            "id": "11111111-2222-3333-4444-555555555551",
            "is_active": False
        })
        assert res.status_code == 200
        assert res.json()["is_active"] is False

        # Plan
        res_plan = client.post("/api/plugins/auto-organizer/sync/plan", json={
            "mapping_id": "11111111-2222-3333-4444-555555555551"
        })
        assert res_plan.status_code == 200
        plan_data = res_plan.json()
        assert plan_data["ok"] is True
        assert "summary" in plan_data
        assert "items" in plan_data

        # Execute
        res_exec = client.post("/api/plugins/auto-organizer/sync/execute", json={
            "mapping_id": "11111111-2222-3333-4444-555555555551"
        })
        assert res_exec.status_code == 200
        assert res_exec.json()["ok"] is True
        assert "synced_at" in res_exec.json()


def test_delete_sync_mapping():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.delete("/api/plugins/auto-organizer/sync/mappings/11111111-2222-3333-4444-555555555553")
        assert res.status_code == 200
        assert res.json()["ok"] is True
