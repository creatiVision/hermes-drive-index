"""
Unit tests for Docker mount discovery, container-host path translation,
and boundary safety validation.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from hermes_auto_organizer.dashboard.plugin_api import router
from hermes_auto_organizer.infrastructure.storage.docker_mounts import (
    DockerMountService,
    docker_mount_service,
    _is_safe_subpath,
)

app = FastAPI()
app.include_router(router, prefix="/api/plugins/auto-organizer")
client = TestClient(app)


def test_docker_mounts_listing():
    mounts = docker_mount_service.get_mounts()
    assert len(mounts) >= 10
    
    # Must include standard Dumpzones and Storage Roots
    downloads = next((m for m in mounts if m["host_path"] == "/home/mb/Downloads"), None)
    assert downloads is not None
    assert downloads["container_path"] == "/opt/data/downloads"
    assert downloads["category"] == "Dumpzone"
    assert downloads["rw"] is True

    privat_buero = next((m for m in mounts if m["host_path"] == "/media/privat-data/10_PrivatBüro"), None)
    assert privat_buero is not None
    assert privat_buero["container_path"] == "/opt/data/privat-buero"
    assert privat_buero["category"] == "Storage Root"


def test_host_to_container_path_translation():
    svc = DockerMountService()
    
    # Downloads folder file
    cpath = svc.translate_to_container_path("/home/mb/Downloads/sub/invoice_2026.pdf")
    assert cpath == "/opt/data/downloads/sub/invoice_2026.pdf"

    # Work data file
    cpath_work = svc.translate_to_container_path("/media/work-data/projects/report.docx")
    assert cpath_work == "/opt/data/work-data/projects/report.docx"

    # Already a container path
    cpath_already = svc.translate_to_container_path("/opt/data/desktop/screenshot.png")
    assert cpath_already == "/opt/data/desktop/screenshot.png"

    # Unmounted host path outside container jail
    unmounted = svc.translate_to_container_path("/etc/passwd")
    assert unmounted is None


def test_container_to_host_path_translation():
    svc = DockerMountService()

    hpath = svc.translate_to_host_path("/opt/data/downloads/invoice.pdf")
    assert hpath == "/home/mb/Downloads/invoice.pdf"

    hpath_privat = svc.translate_to_host_path("/opt/data/privat-buero/Steuern/2026/steuer.pdf")
    assert hpath_privat == "/media/privat-data/10_PrivatBüro/Steuern/2026/steuer.pdf"

    # Already a host path
    hpath_already = svc.translate_to_host_path("/home/mb/Schreibtisch/notes.txt")
    assert hpath_already == "/home/mb/Schreibtisch/notes.txt"


def test_validate_destination_path_allowed():
    svc = DockerMountService()

    # Valid writable path
    res = svc.validate_destination_path("/home/mb/Downloads/Archiv/2026/")
    assert res["valid"] is True
    assert res["is_mounted"] is True
    assert res["is_writable"] is True
    assert res["container_path"] == "/opt/data/downloads/Archiv/2026"


def test_validate_destination_path_read_only():
    svc = DockerMountService()

    # Jules MCP Server is mounted ro
    res = svc.validate_destination_path("/media/xchg/jules-mcp-server/output.txt")
    assert res["valid"] is False
    assert res["is_mounted"] is True
    assert res["is_writable"] is False
    assert "schreibgeschützt" in res["message"]


def test_validate_destination_path_unmounted():
    svc = DockerMountService()

    # Outside docker mounts
    res = svc.validate_destination_path("/var/log/system.log")
    assert res["valid"] is False
    assert res["is_mounted"] is False
    assert "außerhalb der gemounteten Docker-Verzeichnisse" in res["message"]


@patch("hermes_auto_organizer.infrastructure.storage.docker_mounts.DockerMountService.get_mounts")
@patch("hermes_auto_organizer.infrastructure.storage.docker_mounts.docker_mount_service.get_mounts")
def test_mounts_api_endpoints(mock_get_mounts_inst, mock_get_mounts_cls):
    dummy_mounts = [
        {"host_path": "/home/mb/Downloads", "container_path": "/opt/data/downloads", "is_writable": True, "free_gb": 50, "label": "Downloads (Dumpzone)", "rw": True},
        {"host_path": "/media/work-data", "container_path": "/opt/data/work-data", "is_writable": True, "free_gb": 50, "label": "Arbeitsdateien (work-data)", "rw": True},
    ] + [{"host_path": f"/dummy{i}", "container_path": f"/opt/data/dummy{i}", "is_writable": True, "free_gb": 10, "label": f"Dummy{i}", "rw": True} for i in range(6)] + [
        {"host_path": "/ro1", "container_path": "/opt/data/ro1", "is_writable": False, "free_gb": 10, "label": "RO1", "rw": False},
        {"host_path": "/ro2", "container_path": "/opt/data/ro2", "is_writable": False, "free_gb": 10, "label": "RO2", "rw": False},
    ]
    mock_get_mounts_inst.return_value = dummy_mounts
    mock_get_mounts_cls.return_value = dummy_mounts

    # GET /mounts
    res = client.get("/api/plugins/auto-organizer/mounts")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["total_mounts"] >= 10
    assert data["writable_mounts"] >= 8
    assert len(data["mounts"]) == data["total_mounts"]

    # POST /mounts/check (valid)
    chk_res = client.post("/api/plugins/auto-organizer/mounts/check", json={"path": "/home/mb/Downloads/test"})
    assert chk_res.status_code == 200
    chk_data = chk_res.json()
    assert chk_data["valid"] is True

    # POST /mounts/check (invalid / outside container)
    chk_invalid = client.post("/api/plugins/auto-organizer/mounts/check", json={"path": "/root/secret"})
    assert chk_invalid.status_code == 200
    chk_inv_data = chk_invalid.json()
    assert chk_inv_data["valid"] is False
    assert chk_inv_data["is_mounted"] is False


def test_is_safe_subpath():
    assert _is_safe_subpath("/opt/data", "/opt/data/sub/file.txt") is True
    assert _is_safe_subpath("/opt/data", "/opt/data") is True
    assert _is_safe_subpath("/opt/data", "/opt/data_fake/file.txt") is False
    assert _is_safe_subpath("/opt/data", "/opt/data/../secret") is False
    assert _is_safe_subpath("/opt/data", "") is False
    assert _is_safe_subpath("", "/opt/data") is False
    assert _is_safe_subpath(None, "/opt/data") is False
    assert _is_safe_subpath("/opt/data", None) is False

