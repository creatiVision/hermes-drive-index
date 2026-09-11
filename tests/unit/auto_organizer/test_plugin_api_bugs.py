"""
Regression tests for the auto-organizer plugin's 15 API routes.

Verifies connection handling, exception paths, and UUID validation after the
pool-connection fixes. Uses patched `_get_connection` (mocked connections)
and the Hermes plugin route prefix `/api/plugins/auto-organizer/..`.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

import uuid
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hermes_auto_organizer.dashboard import plugin_api as api_module
from hermes_auto_organizer.dashboard.plugin_api import router

BASE = "/api/plugins/auto-organizer"
app = FastAPI()
app.include_router(router, prefix=BASE)
client = TestClient(app)


class FakeRecord:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        return self.data.get(key)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def keys(self):
        return self.data.keys()


def _mock_conn(data=None):
    conn = AsyncMock()
    conn.close = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(
        return_value=FakeRecord(data or {"count": 0, "size": 0, "c": 0, "state": "USER_APPROVED"})
    )
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_conn(conn):
    patcher = patch.object(api_module, "_get_connection", AsyncMock(return_value=conn))
    patcher.start()
    return patcher


# --- Connection handling: routes must return 200 with a mocked conn ---

def test_health_200():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        resp = client.get(f"{BASE}/health")
        assert resp.status_code == 200
        assert resp.json().get("ok") is True
    finally:
        p.stop()


def test_stats_200():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        resp = client.get(f"{BASE}/stats")
        assert resp.status_code == 200
    finally:
        p.stop()


def test_taxonomy_200():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        resp = client.get(f"{BASE}/taxonomy")
        assert resp.status_code == 200
    finally:
        p.stop()


def test_rules_200():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        resp = client.get(f"{BASE}/rules")
        assert resp.status_code == 200
    finally:
        p.stop()


def test_journal_200():
    conn = _mock_conn()
    # journal aggregates; return an empty batch list
    conn.fetch = AsyncMock(return_value=[])
    p = _patch_conn(conn)
    try:
        resp = client.get(f"{BASE}/journal")
        assert resp.status_code == 200
    finally:
        p.stop()


def test_preview_200():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        resp = client.post(f"{BASE}/preview", json={})
        assert resp.status_code == 200
    finally:
        p.stop()


# --- UUID validation: invalid UUID should not 500 ---

def test_taxonomy_node_invalid_uuid_not_500():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        invalid_id = "111111111111111111111111111111111111"
        resp = client.post(
            f"{BASE}/taxonomy/node",
            json={"id": invalid_id, "node_name": "test", "node_path": "/"},
        )
        assert resp.status_code < 500, f"Expected <500, got {resp.status_code}"
    finally:
        p.stop()


def test_rules_toggle_invalid_uuid_not_500():
    conn = _mock_conn()
    p = _patch_conn(conn)
    try:
        invalid_id = "not-a-uuid"
        resp = client.post(f"{BASE}/rules/{invalid_id}/toggle")
        assert resp.status_code < 500, f"Expected <500, got {resp.status_code}"
    finally:
        p.stop()


# --- rule_chat: no AttributeError on dict/Record access ---

def test_rule_chat_no_attribute_error():
    conn = _mock_conn()
    conn.fetchrow = AsyncMock(return_value=FakeRecord({
        "rule_name": "Test Rule",
        "description": "Test",
        "source_pattern": "*",
        "condition_json": "{}",
        "target_path_template": "/",
        "state": "USER_APPROVED",
    }))
    p = _patch_conn(conn)
    try:
        resp = client.post(f"{BASE}/rules/{uuid.uuid4()}/chat", json={"message": "hello"})
        # Should not raise AttributeError; may 503 if DB/LLM unavailable but must not be a 500 from attribute access.
        assert resp.status_code < 500 or "AttributeError" not in resp.text
    finally:
        p.stop()


# --- no connection needed for these routes ---

def test_mounts_no_conn():
    resp = client.get(f"{BASE}/mounts")
    assert resp.status_code == 200


def test_sources_tree_no_conn():
    resp = client.get(f"{BASE}/sources/tree?path=/")
    assert resp.status_code == 200


def test_sources_scan_no_conn():
    resp = client.post(f"{BASE}/sources/scan", json={"roots": []})
    assert resp.status_code == 200