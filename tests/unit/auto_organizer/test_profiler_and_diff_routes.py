"""
Integration tests for Subtree Profiler, Tree-Diff, and Disk Cleaner API routes.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from hermes_auto_organizer.dashboard.plugin_api import router


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_profiler_workflow_routes(client: TestClient, tmp_path: Path):
    # 1. Setup synthetic workspace
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "doc.pdf").write_text("dummy pdf")
    (downloads / "archive.zip").write_text("dummy zip")

    # 2. POST /profiler/scan
    res = client.post("/profiler/scan", json={"path": str(tmp_path), "max_depth": 4})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "mime_entropy" in data["data"]
    assert "total_files" in data["data"]

    # 3. GET /profiler/outliers
    res_outliers = client.get("/profiler/outliers")
    assert res_outliers.status_code == 200
    assert "outliers" in res_outliers.json()

    # 4. GET /profiler/rules
    res_rules = client.get("/profiler/rules")
    assert res_rules.status_code == 200
    assert "rules" in res_rules.json()

    # 5. GET /profiler/tree-diff
    res_diff = client.get("/profiler/tree-diff")
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert diff_data["ok"] is True
    assert "tree_diff" in diff_data

    # 6. POST /profiler/export-obsidian
    vault = tmp_path / "Vault"
    res_export = client.post("/profiler/export-obsidian", json={"vault_path": str(vault)})
    assert res_export.status_code == 200
    assert res_export.json()["ok"] is True
    assert (vault / "Auto-Organizer" / "🌳 Lan-Tree Graph Index.md").exists()

    # 7. POST /profiler/execute
    res_exec = client.post("/profiler/execute", json={"only_approved": True})
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["ok"] is True
    assert "batch_id" in exec_data

    # 8. POST /profiler/rollback
    res_rb = client.post("/profiler/rollback", json={"batch_id": exec_data["batch_id"]})
    assert res_rb.status_code == 200
    assert res_rb.json()["ok"] is True


def test_cleaner_and_mesh_routes(client: TestClient, tmp_path: Path):
    # 1. GET /cleaner/mounts
    res_mounts = client.get("/cleaner/mounts")
    assert res_mounts.status_code == 200
    assert "mounts" in res_mounts.json()

    # 2. POST /cleaner/analyze
    test_dir = tmp_path / "analyze_dir"
    test_dir.mkdir()
    (test_dir / "sample.bin").write_bytes(b"A" * 1024)
    res_analyze = client.post("/cleaner/analyze", json={"path": str(test_dir)})
    assert res_analyze.status_code == 200
    assert res_analyze.json()["count"] >= 1

    # 3. POST /cleaner/candidates
    res_cand = client.post("/cleaner/candidates", json={
        "candidates": [
            {"path": "/tmp/test_cache", "size": 100, "level": 0, "reason": "cache"},
        ]
    })
    assert res_cand.status_code == 200
    assert res_cand.json()["ok"] is True

    # 4. GET /mesh/overview
    res_mesh = client.get("/mesh/overview")
    assert res_mesh.status_code == 200
    assert "active_hosts" in res_mesh.json()["mesh"]

    # 5. GET /mesh/root-triage
    res_triage = client.get("/mesh/root-triage")
    assert res_triage.status_code == 200
    assert "candidates" in res_triage.json()


def test_profiler_remote_node_routes(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from hermes_auto_organizer.domain.profiler_models import FolderProfile
    from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import SSHNodeInspector

    fake_profile = FolderProfile(
        path="/media/sdc2-2tb-work-privat-xchg",
        name="sdc2-2tb-work-privat-xchg",
        depth=0,
        direct_files_count=10,
        direct_bytes=1000,
        total_files_count=100,
        total_bytes=100000,
        subfolders=[
            FolderProfile(
                path="/media/sdc2-2tb-work-privat-xchg/models_backup",
                name="models_backup",
                depth=1,
                direct_files_count=1,
                direct_bytes=5 * 1024 * 1024 * 1024,
                total_files_count=1,
                total_bytes=5 * 1024 * 1024 * 1024,
            )
        ]
    )

    monkeypatch.setattr(
        SSHNodeInspector,
        "profile_remote_subtree",
        lambda self, node_id, remote_path, max_depth, include_hidden: fake_profile,
    )

    res = client.post("/profiler/scan", json={
        "path": "/media/sdc2-2tb-work-privat-xchg",
        "node_id": "debian1",
        "max_depth": 2,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["data"]["node_id"] == "debian1"
    assert data["data"]["root_path"] == "/media/sdc2-2tb-work-privat-xchg"

    # Outliers should contain models_backup
    res_out = client.get("/profiler/outliers")
    assert res_out.status_code == 200
    assert res_out.json()["node_id"] == "debian1"
    outliers = res_out.json()["outliers"]
    assert any("models_backup" in o["source_path"] for o in outliers)

    # Tree-diff should reflect debian1 node
    res_diff = client.get("/profiler/tree-diff")
    assert res_diff.status_code == 200
    assert res_diff.json()["node_id"] == "debian1"

