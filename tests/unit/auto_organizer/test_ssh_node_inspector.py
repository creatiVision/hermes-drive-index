"""
Unit and integration tests for SSH Node Inspector, SSHNodeService, and API routes.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from hermes_auto_organizer.application.use_cases.ssh_node_service import SSHNodeService
from hermes_auto_organizer.dashboard.plugin_api import router
from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import SSHNodeInspector


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_ssh_node_inspector_offline_handling():
    # Configure an unreachable host
    inspector = SSHNodeInspector(node_configs={
        "test_node": {
            "name": "fake-host",
            "candidate_hosts": ["192.0.2.1"],  # TEST-NET-1 unroutable
            "user": "fake",
            "key_path": "/nonexistent/key",
            "port": 2222,
        }
    })

    conn = inspector.test_connection("test_node")
    assert conn["ok"] is False
    assert conn["is_online"] is False
    assert "error" in conn

    mounts = inspector.get_node_mounts("test_node")
    assert mounts == []

    services = inspector.get_node_docker_services("test_node")
    assert services == []


def test_ssh_node_inspector_mount_and_docker_parsing():
    inspector = SSHNodeInspector()

    # Test mount parsing with synthetic df output
    fake_df = (
        "Filesystem     Type      1B-blocks          Used     Available Use% Mounted on\n"
        "/dev/nvme1n1p1 ext4   251214000000  106300000000  132140000000  45% /\n"
        "/dev/sda2      ext4  1948156166144  982681686016  866438000640  54% /media/sdc2-2tb-work-privat-xchg\n"
        "/dev/sdc1      ext4 10000000000000 9700000000000  300000000000  97% /media/ext10tb\n"
    )

    with patch.object(inspector, "execute_remote", return_value=(True, fake_df, 15.0)):
        mounts = inspector.get_node_mounts("debian1")
        assert len(mounts) == 3
        shared = next((m for m in mounts if m["mounted_on"] == "/media/sdc2-2tb-work-privat-xchg"), None)
        assert shared is not None
        assert shared["is_shared_pool"] is True
        assert shared["used_percent"] == 54.0

        cold = next((m for m in mounts if m["mounted_on"] == "/media/ext10tb"), None)
        assert cold is not None
        assert cold["is_cold_backup"] is True
        assert cold["used_percent"] == 97.0

    # Test docker ps parsing with synthetic JSON lines
    fake_docker = (
        '{"ID":"a1b2c3d4e5f6","Names":"shared-pg","Image":"postgres:16","Status":"Up 4 hours","Ports":"0.0.0.0:5432->5432/tcp"}\n'
        '{"ID":"f6e5d4c3b2a1","Names":"portainer-debian1","Image":"portainer/portainer-ce","Status":"Up 4 hours","Ports":"9443/tcp"}\n'
    )
    with patch.object(inspector, "execute_remote", return_value=(True, fake_docker, 12.0)):
        services = inspector.get_node_docker_services("debian1")
        assert len(services) == 2
        pg = next((s for s in services if s["name"] == "shared-pg"), None)
        assert pg is not None
        assert pg["is_database"] is True


def test_ssh_node_service():
    mock_inspector = MagicMock(spec=SSHNodeInspector)
    mock_inspector.test_connection.return_value = {
        "ok": True,
        "is_online": True,
        "host": "192.168.178.89",
        "hostname": "debian1",
        "uptime": "up 4 hours",
        "kernel": "6.12",
        "latency_ms": 25.0,
    }
    mock_inspector.get_node_status.return_value = {
        "ok": True,
        "load_avg": [0.5, 0.8, 1.1],
        "mem_total_bytes": 16000000000,
        "mem_avail_bytes": 8000000000,
        "mem_used_pct": 50.0,
    }
    mock_inspector.get_node_mounts.return_value = [
        {"mounted_on": "/media/sdc2-2tb-work-privat-xchg", "is_shared_pool": True, "used_percent": 50.0}
    ]
    mock_inspector.get_node_docker_services.return_value = [
        {"name": "shared-pg", "status": "Up 4 hours"}
    ]

    service = SSHNodeService(mock_inspector)
    summary = service.get_nodes_summary()
    assert len(summary) == 1
    assert summary[0]["is_online"] is True
    assert summary[0]["host"] == "192.168.178.89"

    overview = service.get_node_overview("debian1")
    assert overview["ok"] is True
    assert overview["hostname"] == "debian1"
    assert overview["shared_pool_mount"] is not None
    assert overview["active_containers_count"] == 1


def test_ssh_api_routes(client: TestClient):
    # 1. GET /ssh/nodes
    res_nodes = client.get("/ssh/nodes")
    assert res_nodes.status_code == 200
    data = res_nodes.json()
    assert data["ok"] is True
    assert "nodes" in data
    assert any(n["node_id"] == "debian1" for n in data["nodes"])

    # 2. POST /ssh/test
    res_test = client.post("/ssh/test", json={"node_id": "debian1"})
    assert res_test.status_code == 200
    assert "ok" in res_test.json()

    # 3. GET /ssh/debian1/overview
    res_overview = client.get("/ssh/debian1/overview")
    assert res_overview.status_code == 200
    assert "ok" in res_overview.json()
