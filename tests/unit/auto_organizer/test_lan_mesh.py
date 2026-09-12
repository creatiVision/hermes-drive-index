"""Tests for LanMeshScanner and LanMeshUseCase."""

from pathlib import Path
import pytest

from hermes_auto_organizer.application.use_cases.lan_mesh_service import LanMeshUseCase
from hermes_auto_organizer.infrastructure.storage.lan_mesh_scanner import LanMeshScanner


def test_lan_mesh_scanner_devices():
    scanner = LanMeshScanner()
    devices = scanner.get_devices()
    assert len(devices) == 3
    names = [d["name"] for d in devices]
    assert "laptop" in names
    assert "debian1" in names
    assert any("Note14new" in n for n in names)


def test_lan_mesh_use_case_overview(tmp_path: Path):
    # Create fake syncthing config
    fake_config = tmp_path / "config.xml"
    fake_config.write_text("""<configuration version="37">
        <folder id="test-folder" label="Test" path="/tmp/test" type="sendreceive">
            <device id="DEV1" />
            <device id="DEV2" />
        </folder>
        <device id="DEV1" name="laptop" />
        <device id="DEV2" name="debian1" />
    </configuration>""")

    scanner = LanMeshScanner(syncthing_config_path=str(fake_config))
    use_case = LanMeshUseCase(scanner)

    overview = use_case.get_mesh_overview()
    assert overview["network_name"] == "creatiVision AI-LAN"
    assert len(overview["devices"]) == 3
    assert overview["syncthing_folders_count"] == 1
    assert overview["syncthing_folders"][0]["id"] == "test-folder"
