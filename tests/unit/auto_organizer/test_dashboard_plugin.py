"""
Unit tests for the consolidated Auto-Organizer plugin API (15 routes).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from hermes_auto_organizer.dashboard import plugin_api as api_module
from hermes_auto_organizer.dashboard.plugin_api import router

app = FastAPI()
app.include_router(router, prefix="/api/plugins/auto-organizer")
client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_pool():
    api_module._db_pool = None
    yield
    api_module._db_pool = None


# --- Manifest ---

def test_manifest_structure():
    manifest_path = (
        Path(__file__).parents[3]
        / "src"
        / "hermes_auto_organizer"
        / "dashboard"
        / "manifest.json"
    )
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["name"] == "auto-organizer"
    assert data["tab"]["path"] == "/organizer"
    assert data["entry"] == "dist/index.js"
    assert data["api"] == "plugin_api.py"


def test_dist_js_exists():
    dist_js = (
        Path(__file__).parents[3]
        / "src"
        / "hermes_auto_organizer"
        / "dashboard"
        / "dist"
        / "index.js"
    )
    assert dist_js.exists()
    assert dist_js.stat().st_size > 1000


# --- Health ---

def test_health_disconnected():
    with patch.object(api_module, "_get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["plugin"] == "auto-organizer"
        assert data["database_connected"] is False


def test_health_connected():
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"c": 9}
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["database_connected"] is True
        assert data["table_count"] == 9


# --- Stats ---

def test_stats_endpoint():
    mock_conn = AsyncMock()
    mock_conn.fetchrow.side_effect = [
        {"count": 142, "size": 104857600},
        {"count": 4},
        {"count": 3},
        {"count": 5},
        {"count": 2},
    ]
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total_files"] == 142
        assert data["total_size_mb"] == 100.0
        assert data["open_anomalies"] == 3
        assert data["active_rules"] == 5


# --- Mounts ---

def test_mounts_endpoint():
    res = client.get("/api/plugins/auto-organizer/mounts")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["total_mounts"] >= 1
    assert isinstance(data["mounts"], list)


# --- Sources tree ---

def test_sources_tree_root():
    res = client.get("/api/plugins/auto-organizer/sources/tree?path=/")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["path"] == "/"
    assert "children" in data


def test_sources_tree_no_cache_fallback():
    with patch.object(api_module, "_find_system_tree_file", return_value=None):
        res = client.get("/api/plugins/auto-organizer/sources/tree?path=/")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert "children" in data
        assert len(data["children"]) >= 1


# --- Taxonomy ---

def test_taxonomy_db_empty_returns_defaults():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = None
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/taxonomy")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert "tree" in data
        assert data["total_nodes"] >= 1


def test_taxonomy_create_node():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "INSERT 1"
    mock_conn.fetchrow.return_value = {
        "id": str(uuid4()),
        "parent_id": None,
        "node_name": "Steuern",
        "node_path": "/media/privat-buero/Steuern",
        "icon": None,
        "description": None,
        "keywords": [],
        "confidence": 1.0,
        "state": "approved",
        "source": "manual",
    }
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.post(
            "/api/plugins/auto-organizer/taxonomy/node",
            json={
                "node_name": "Steuern",
                "node_path": "/media/privat-buero/Steuern",
                "state": "approved",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["node"]["node_name"] == "Steuern"


# --- Rules ---

def test_rules_list_with_db():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": uuid4(),
            "rule_name": "Invoices",
            "description": "Archive invoices",
            "source_pattern": "*",
            "condition_json": json.dumps({"match_mode": "all", "conditions": []}),
            "target_path_template": "/media/privat-buero/Steuern/{year}/",
            "state": "USER_APPROVED",
            "dry_run_last_count": 5,
        }
    ]
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/rules")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["total"] >= 1
        assert len(data["adopted"]) >= 1
        assert data["adopted"][0]["rule_name"] == "Invoices"
        assert len(data["suggested"]) >= 1


def test_rules_list_db_unavailable():
    with patch.object(api_module, "_get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/rules")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["total"] >= 1
        assert len(data["suggested"]) >= 1
        assert data["adopted"] == []


def test_rules_create():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "INSERT 1"
    # fetchrow is called twice: 1) existing rule check (None), 2) fetch after save (row)
    mock_conn.fetchrow.side_effect = [
        None,  # no existing rule
        {"id": uuid4(), "rule_name": "Rechnungen", "description": "Archive PDFs",
         "source_pattern": "*", "condition_json": json.dumps({"match_mode": "all", "conditions": []}),
         "target_path_template": "/media/privat-buero/Steuern/{year}/",
         "state": "USER_APPROVED", "source": "user",
         "created_at": None, "updated_at": None},
    ]
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.post(
            "/api/plugins/auto-organizer/rules",
            json={
                "rule_name": "Rechnungen",
                "description": "Archive PDFs",
                "source_pattern": "*",
                "condition_json": {"match_mode": "all", "conditions": []},
                "target_path_template": "/media/privat-buero/Steuern/{year}/",
                "state": "USER_APPROVED",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True


def test_rules_toggle():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "UPDATE 1"
    mock_conn.fetchrow.return_value = {"id": uuid4(), "state": "USER_APPROVED"}
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        test_uuid = str(uuid4())
        res = client.post(
            f"/api/plugins/auto-organizer/rules/{test_uuid}/toggle",
            json={},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True


# --- Preview ---

def test_preview_no_rules():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.post("/api/plugins/auto-organizer/preview", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["batch_id"].startswith("dry_")
        assert data["actions"] == []
        assert data["summary"]["total"] == 0


# --- Journal ---

def test_journal_empty():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/journal")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["batches"] == []


def test_journal_with_batch():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "batch_id": uuid4(),
            "executed_at": datetime.now(timezone.utc),
            "file_count": 5,
            "rule_ids": [uuid4()],
        }
    ]
    with patch.object(api_module, "_get_connection", return_value=mock_conn):
        res = client.get("/api/plugins/auto-organizer/journal")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert len(data["batches"]) == 1
        assert data["batches"][0]["file_count"] == 5


def test_journal_db_unavailable():
    with patch.object(api_module, "_get_connection", return_value=None):
        res = client.get("/api/plugins/auto-organizer/journal")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["batches"] == []


# --- Route count ---

def test_route_count():
    assert len(router.routes) == 15, f"Expected 15 routes, got {len(router.routes)}"
