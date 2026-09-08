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


def test_proactive_scan_and_start_indexing():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        # 1. Proactive Scan
        res = client.get("/api/plugins/auto-organizer/discovery/proactive-scan")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["AWAITING_CONSENT", "INDEXED"]
        assert data["total_drives"] >= 5
        assert "indexing_prompt" in data
        assert any("Downloads" in d["name"] for d in data["drives"])

        # 2. Start Indexing
        res_idx = client.post("/api/plugins/auto-organizer/discovery/start-indexing", json={
            "enable_embeddings": True,
            "ocr_enabled": True
        })
        assert res_idx.status_code == 200
        idx_data = res_idx.json()
        assert idx_data["ok"] is True
        assert idx_data["status"] == "INDEXED"
        assert idx_data["indexed_file_count"] >= 500


def test_emergent_taxonomy_and_approval():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        # 1. Fetch emergent taxonomy
        res = client.get("/api/plugins/auto-organizer/taxonomy/emergent")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert len(data["categories"]) >= 4
        cat_names = [c["name"] for c in data["categories"]]
        assert "01_Privat" in cat_names
        assert "02_Geschaeftlich" in cat_names
        assert "03_Geschaeftl_Projekte" in cat_names
        assert "04_Backup_Archiv" in cat_names

        # Verify data evidence is present
        privat = next(c for c in data["categories"] if c["name"] == "01_Privat")
        assert "data_evidence" in privat
        assert privat["confidence"] >= 0.9

        # 2. Approve emergent taxonomy
        res_app = client.post("/api/plugins/auto-organizer/taxonomy/emergent/approve", json={
            "approved": True
        })
        assert res_app.status_code == 200
        assert res_app.json()["is_approved"] is True


def test_cross_drive_reconciliation_and_clarification():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        # 1. Get cross-drive reconciliation clusters
        res = client.get("/api/plugins/auto-organizer/reconciliation/cross-drive")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["total_clusters"] >= 3
        clusters = data["clusters"]
        assert any(c["id"] == "cluster_accounting_2025" for c in clusters)
        assert any(c["redundancy_type"] == "suspected_backup" for c in clusters)
        assert any(c["redundancy_type"] == "dump_zone_duplicate" for c in clusters)

        # Verify semantic questions are present
        first = clusters[0]
        assert "semantic_question" in first
        assert "recommendation" in first

        # 2. Clarify redundancy
        res_clarify = client.post("/api/plugins/auto-organizer/reconciliation/clarify", json={
            "cluster_id": "cluster_accounting_2025",
            "decision": "intended_backup",
            "notes": "Beabsichtigtes Cloud-Backup für Buchhaltung 2025"
        })
        assert res_clarify.status_code == 200
        clarify_data = res_clarify.json()
        assert clarify_data["ok"] is True
        assert clarify_data["decision"] == "intended_backup"


def test_system_tree_endpoint():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/system-tree")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert "summary" in data
        assert data["summary"]["total_hosts"] == 5
        assert "hosts" in data
        assert len(data["hosts"]) == 5
        assert "syncthing" in data
        assert "backup_registry" in data
        assert "docker_backup" in data["backup_registry"]
        assert "pg_backup" in data["backup_registry"]
        assert "tree" in data
        assert len(data["tree"]) == 5

        # Check laptop node
        laptop = next((h for h in data["tree"] if h["computer_id"] == "kimi-laptop"), None)
        assert laptop is not None
        assert laptop["status"]["symbol"] == "🟢"
        assert len(laptop["children"]) >= 4

        # Check debian1 node
        debian = next((h for h in data["tree"] if h["computer_id"] == "kimi-debian1"), None)
        assert debian is not None
        assert any(c["id"] == "drive_debian1_docker" for c in debian["children"])

        # Check mobile node
        mobile = next((h for h in data["tree"] if h["computer_id"] == "note14new"), None)
        assert mobile is not None
        assert any(c["id"] == "drive_mobile_share" for c in mobile["children"])


def test_filesystem_tree_full_endpoint():
    res = client.get("/api/plugins/auto-organizer/filesystem-tree/full")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "summary" in data
    assert "total_mounts" in data["summary"]
    assert "total_directories_scanned" in data["summary"]
    assert "total_files_discovered" in data["summary"]
    assert "total_files_indexed_in_db" in data["summary"]
    assert "total_reorg_moves_pending" in data["summary"]
    assert "mounts" in data
    assert len(data["mounts"]) >= 1

    # Verify root mount node properties
    first_mount = data["mounts"][0]
    assert "path" in first_mount
    assert "node_type" in first_mount
    assert "permissions" in first_mount
    assert "indexing" in first_mount
    assert "reorganization" in first_mount
    assert "syncthing" in first_mount
    assert "backup" in first_mount


def test_filesystem_tree_browse_endpoint():
    from unittest.mock import MagicMock
    mock_scandir = MagicMock()
    mock_scandir.__enter__.return_value = []
    with patch("os.path.exists", return_value=True), \
         patch("os.path.isdir", return_value=True), \
         patch("os.scandir", return_value=mock_scandir):
        res = client.get("/api/plugins/auto-organizer/filesystem-tree/browse?path=/media/work-data")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["path"] == "/media/work-data"
        assert "children" in data
        assert isinstance(data["children"], list)


def test_filesystem_tree_rescan_endpoint():
    res = client.post("/api/plugins/auto-organizer/filesystem-tree/rescan")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "message" in data


def test_suggested_rule_switch_endpoint():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        # Approve
        res = client.post("/api/plugins/auto-organizer/rules/suggested/switch", json={"rule_id": "rule_test_1", "state": "approved"})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["state"] == "approved"
        assert "rule_test_1" in data["approved_rules"]

        # Exclude
        res = client.post("/api/plugins/auto-organizer/rules/suggested/switch", json={"rule_id": "rule_test_1", "state": "excluded"})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["state"] == "excluded"
        assert "rule_test_1" in data["excluded_rules"]
        assert "rule_test_1" not in data["approved_rules"]

        # Reset to proposed
        res = client.post("/api/plugins/auto-organizer/rules/suggested/switch", json={"rule_id": "rule_test_1", "state": "proposed"})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["state"] == "proposed"
        assert "rule_test_1" not in data["approved_rules"]
        assert "rule_test_1" not in data["excluded_rules"]


def test_emergent_category_switch_endpoint():
    # Approve category
    res = client.post("/api/plugins/auto-organizer/taxonomy/emergent/category-switch", json={"category_id": "cat_test_fin", "state": "approved"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["state"] == "approved"
    assert "cat_test_fin" in data["approved_category_ids"]

    # Exclude category
    res = client.post("/api/plugins/auto-organizer/taxonomy/emergent/category-switch", json={"category_id": "cat_test_fin", "state": "excluded"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["state"] == "excluded"
    assert "cat_test_fin" in data["excluded_category_ids"]
    assert "cat_test_fin" not in data["approved_category_ids"]


def test_adopt_suggested_rules_offline_fallback():
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=None):
        res = client.post("/api/plugins/auto-organizer/rules/adopt-suggested", json={"adopt_all": True})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["adopted_count"] >= 1


