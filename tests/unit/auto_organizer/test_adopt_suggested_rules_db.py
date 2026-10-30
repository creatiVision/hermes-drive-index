import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from hermes_auto_organizer.dashboard.plugin_api import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/plugins/auto-organizer")
client = TestClient(app)

class FakeDBConnection:
    def __init__(self, existing_rows):
        self.existing_rows = existing_rows
        self.fetch_called = False
        self.executemany_updates = []
        self.executemany_inserts = []

    async def fetch(self, query, aliases):
        self.fetch_called = True
        res = []
        for r in self.existing_rows:
            if r["rule_name"] in aliases:
                res.append(r)
        return res

    async def executemany(self, query, params):
        if "UPDATE" in query:
            self.executemany_updates.extend(params)
        elif "INSERT" in query:
            self.executemany_inserts.extend(params)

    async def close(self):
        pass

def test_adopt_suggested_rules_batch_db():
    fake_existing = [
        {"id": "uuid-1111", "rule_name": "Verträge & Vereinbarungen konsolidieren"},
    ]
    mock_conn = FakeDBConnection(fake_existing)

    mock_suggestions = [
        {
            "id": "sug_1",
            "name": "Verträge & Policen konsolidieren",
            "description": "Desc 1",
            "condition_json": {"ext": ".pdf"},
            "target_template": "/contracts",
            "matched_files_count": 5,
        },
        {
            "id": "sug_2",
            "name": "New Unseen Rule",
            "description": "Desc 2",
            "condition_json": {"ext": ".docx"},
            "target_template": "/docs",
            "matched_files_count": 2,
        },
    ]

    async def mock_get_suggested_rules():
        return {"suggested_rules": mock_suggestions}

    with patch("hermes_auto_organizer.dashboard.plugin_api.get_suggested_rules", side_effect=mock_get_suggested_rules), \
         patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", return_value=mock_conn):

        res = client.post("/api/plugins/auto-organizer/rules/adopt-suggested", json={"adopt_all": True})
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["adopted_count"] == 2

        assert mock_conn.fetch_called is True
        assert len(mock_conn.executemany_updates) == 1
        assert mock_conn.executemany_updates[0] == ("uuid-1111",)

        assert len(mock_conn.executemany_inserts) == 1
        insert_param = mock_conn.executemany_inserts[0]
        assert insert_param[1] == "New Unseen Rule"
        assert insert_param[2] == "Desc 2"
        assert insert_param[4] == "/docs"
        assert insert_param[5] == 2
