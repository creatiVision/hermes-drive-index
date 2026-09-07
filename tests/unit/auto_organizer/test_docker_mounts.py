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


def test_mounts_api_endpoints():
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
