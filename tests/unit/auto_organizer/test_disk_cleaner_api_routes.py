"""Tests for newly integrated ai-disk-cleaner and LAN mesh routes in plugin_api.py."""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hermes_auto_organizer.dashboard.plugin_api import router

BASE = "/api/plugins/auto-organizer"
app = FastAPI()
app.include_router(router, prefix=BASE)
client = TestClient(app)


def test_get_disk_usages():
    resp = client.get(f"{BASE}/disk/usages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "mounts" in data
    assert isinstance(data["mounts"], list)


def test_analyze_disk_path(tmp_path: Path):
    test_dir = tmp_path / "test_analyze"
    test_dir.mkdir()
    (test_dir / "file_a.txt").write_bytes(b"12345")
    (test_dir / "file_b.txt").write_bytes(b"6789012345")

    # JSON format
    resp = client.get(f"{BASE}/disk/analyze?path={test_dir}&format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["format"] == "json"
    assert data["entries_count"] >= 2

    # CSV format
    resp_csv = client.get(f"{BASE}/disk/analyze?path={test_dir}&format=csv")
    assert resp_csv.status_code == 200
    csv_data = resp_csv.json()
    assert csv_data["ok"] is True
    assert "path,totalSize,type" in csv_data["data"]


def test_trash_candidates_endpoints():
    payload = {
        "candidates": [
            {"path": "/tmp/test_cache", "size": 4096, "level": 0, "reason": "Cache junk"},
            {"path": "/home/mb/Downloads/large.iso", "size": 1048576, "level": 1, "reason": "Old ISO"},
        ]
    }

    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", new_callable=AsyncMock) as mock_conn, \
         patch("hermes_auto_organizer.dashboard.plugin_api._release_conn", new_callable=AsyncMock):
        mock_conn.return_value = None  # test graceful degradation when DB is absent
        resp = client.post(f"{BASE}/disk/candidates", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["added_count"] == 2

        resp_get = client.get(f"{BASE}/disk/candidates")
        assert resp_get.status_code == 200
        assert resp_get.json()["ok"] is True


def test_migration_and_rollback_route(tmp_path: Path):
    source = tmp_path / "source_folder"
    source.mkdir()
    (source / "data.bin").write_bytes(b"important data")
    dest_dir = tmp_path / "target_drive"
    dest_dir.mkdir()

    payload = {
        "source_path": str(source),
        "destination_dir": str(dest_dir),
        "name": "migrated_folder",
    }

    with patch("hermes_auto_organizer.dashboard.plugin_api._get_connection", new_callable=AsyncMock) as mock_conn, \
         patch("hermes_auto_organizer.dashboard.plugin_api._release_conn", new_callable=AsyncMock):
        mock_conn.return_value = None
        resp = client.post(f"{BASE}/disk/migrate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        mig = data["migration"]
        assert mig["source_path"] == str(source)
        assert mig["symlink_created"] is True
        assert source.is_symlink()

        # List migrations
        resp_list = client.get(f"{BASE}/disk/migrations")
        assert resp_list.status_code == 200


def test_lan_mesh_and_root_triage():
    resp_mesh = client.get(f"{BASE}/lan/mesh")
    assert resp_mesh.status_code == 200
    mesh = resp_mesh.json()
    assert mesh["ok"] is True
    assert "devices" in mesh
    assert "syncthing_folders" in mesh

    resp_triage = client.get(f"{BASE}/lan/root-triage")
    assert resp_triage.status_code == 200
    triage = resp_triage.json()
    assert triage["ok"] is True
    assert "candidates" in triage


def test_sync_mappings():
    resp = client.get(f"{BASE}/sync/mappings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] >= 1
    assert data["mappings"][0]["name"] == "Peterstor WEG & Mieter 2024"
