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


def test_lan_mesh_root_triage_execution_and_rollback(tmp_path: Path):
    source_dir = tmp_path / "source_root"
    source_dir.mkdir()
    target_dir = tmp_path / "target_subfolder"

    file1 = source_dir / "tutorial.mp4"
    file1.write_text("dummy video content")
    file2 = source_dir / "bank_statement.pdf"
    file2.write_text("dummy bank content")

    class FakeAdapter:
        def get_devices(self):
            return []
        def get_syncthing_folders(self):
            return []
        def get_root_triage(self):
            return [
                {
                    "source_path": str(file1),
                    "suggested_destination": str(target_dir),
                    "category": "it_tutorial_video",
                },
                {
                    "source_path": str(file2),
                    "suggested_destination": str(target_dir),
                    "category": "banking_records",
                }
            ]

    use_case = LanMeshUseCase(FakeAdapter())
    exec_res = use_case.execute_root_triage()
    assert exec_res["ok"] is True
    assert exec_res["executed_count"] == 2
    assert not file1.exists()
    assert not file2.exists()
    assert (target_dir / "tutorial.mp4").exists()
    assert (target_dir / "bank_statement.pdf").exists()

    # Rollback
    rollback_res = use_case.rollback_root_triage(exec_res["batch_id"])
    assert rollback_res["ok"] is True
    assert rollback_res["reverted_count"] == 2
    assert file1.exists()
    assert file2.exists()
    assert not (target_dir / "tutorial.mp4").exists()
    assert not (target_dir / "bank_statement.pdf").exists()

