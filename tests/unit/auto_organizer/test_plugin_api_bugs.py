import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import uuid

from hermes_auto_organizer.dashboard.plugin_api import router

app = FastAPI()
app.include_router(router, prefix="/api")
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

@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.close = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=FakeRecord({"count": 0, "size": 0, "c": 0, "state": "USER_APPROVED"}))
    conn.execute = AsyncMock(return_value=None)
    return conn

@pytest.mark.xfail(reason="Bug: Connection is closed instead of released to pool")
def test_health_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        mock_conn.close.assert_not_called()

@pytest.mark.xfail(reason="Bug: Connection is closed instead of released to pool")
def test_stats_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        mock_conn.close.assert_not_called()

@pytest.mark.xfail(reason="Bug: Connection is never closed or released (leak)")
def test_taxonomy_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.get("/api/taxonomy")
        assert resp.status_code == 200
        # The test should expect the connection to be cleaned up
        assert mock_conn.close.call_count == 1 or getattr(mock_conn, 'release', AsyncMock()).call_count == 1

@pytest.mark.xfail(reason="Bug: UUID parsing crashes on invalid UUID string lengths")
def test_taxonomy_node_invalid_uuid(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        invalid_id = "111111111111111111111111111111111111"
        resp = client.post("/api/taxonomy/node", json={"id": invalid_id, "node_name": "test", "node_path": "/"})
        assert resp.status_code in (400, 422)

@pytest.mark.xfail(reason="Bug: Connection is never closed or released (leak)")
def test_rules_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.get("/api/rules")
        assert resp.status_code == 200
        assert mock_conn.close.call_count == 1 or getattr(mock_conn, 'release', AsyncMock()).call_count == 1

@pytest.mark.xfail(reason="Bug: Connection is closed instead of released to pool")
def test_post_rules_connection_handling(mock_conn):
    mock_conn.fetchrow.return_value = FakeRecord({"id": uuid.uuid4(), "rule_name": "Test", "description": None, "source_pattern": "*", "condition_json": "{}", "target_path_template": "/", "state": "USER_APPROVED", "source": "user"})
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.post("/api/rules", json={"rule_name": "Test", "target_path_template": "/"})
        assert resp.status_code == 200
        mock_conn.close.assert_not_called()

@pytest.mark.xfail(reason="Bug: Accessing rule_row.rule_name on dict-like Record causes AttributeError")
def test_rule_chat_attribute_error(mock_conn):
    mock_conn.fetchrow.return_value = FakeRecord({
        "rule_name": "Test Rule",
        "description": "Test",
        "source_pattern": "*",
        "condition_json": "{}",
        "target_path_template": "/",
        "state": "USER_APPROVED"
    })
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.post(f"/api/rules/{uuid.uuid4()}/chat", json={"message": "hello"})
        assert resp.status_code == 200

@pytest.mark.xfail(reason="Bug: Connection is closed instead of released to pool")
def test_post_rules_toggle_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.post(f"/api/rules/{uuid.uuid4()}/toggle")
        assert resp.status_code == 200
        mock_conn.close.assert_not_called()

@pytest.mark.xfail(reason="Bug: Connection is closed instead of released to pool")
def test_post_preview_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.post("/api/preview", json={})
        assert resp.status_code == 200
        mock_conn.close.assert_not_called()

@pytest.mark.xfail(reason="Bug: Connection is never closed or released (leak)")
def test_post_execute_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.post("/api/execute", json={})
        assert resp.status_code == 200
        assert mock_conn.close.call_count == 1 or getattr(mock_conn, 'release', AsyncMock()).call_count == 1

@pytest.mark.xfail(reason="Bug: Connection is closed instead of released to pool")
def test_journal_connection_handling(mock_conn):
    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):
        resp = client.get("/api/journal")
        assert resp.status_code == 200
        mock_conn.close.assert_not_called()

@pytest.mark.xfail(reason="Bug: Accessing .value on None rollback_state causes AttributeError")
def test_rollback_none_dereference(mock_conn):
    class FakeRollbackRecord:
        def __init__(self):
            self.rollback_state = None

    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn), \
         patch("hermes_auto_organizer.dashboard.plugin_api.PostgresExecutionLedger") as MockLedger:
        mock_ledger_instance = MockLedger.return_value
        mock_ledger_instance.list_batch_records = AsyncMock(return_value=[FakeRollbackRecord()])
        resp = client.post(f"/api/journal/{uuid.uuid4()}/rollback")
        assert resp.status_code == 200

def test_mounts_no_conn_needed():
    resp = client.get("/api/mounts")
    assert resp.status_code == 200

def test_sources_tree_no_conn_needed():
    resp = client.get("/api/sources/tree?path=/")
    assert resp.status_code == 200

def test_sources_scan_no_conn_needed():
    resp = client.post("/api/sources/scan", json={"roots": ["/tmp"]})
    assert resp.status_code == 200
