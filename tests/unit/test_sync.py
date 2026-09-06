from __future__ import annotations

from pathlib import Path

from hermes_drive_index.core.local_scanner import LocalFile
from hermes_drive_index.core.models import DriveFile
from hermes_drive_index.core.sync import SyncMapping, plan_selective_sync


def test_plan_selective_sync_detects_uploads_and_downloads(tmp_path: Path):
    mapping = SyncMapping(
        name="test_sync",
        local_path=tmp_path,
        drive_folder_path="Personal Files/SyncDir",
        direction="bidirectional",
    )

    local_files = [
        LocalFile("l1", "local_only.txt", "text/plain", str(tmp_path / "local_only.txt"), 100, "2026-01-01T00:00:00Z", relative_path="local_only.txt"),
        LocalFile("l2", "shared.txt", "text/plain", str(tmp_path / "shared.txt"), 200, "2026-01-01T00:00:00Z", md5_checksum="hash1", relative_path="shared.txt"),
    ]

    drive_files = [
        DriveFile("d1", "remote_only.txt", "text/plain", "Personal Files/SyncDir/remote_only.txt", 150, "2026-01-01T00:00:00Z", None, None),
        DriveFile("d2", "shared.txt", "text/plain", "Personal Files/SyncDir/shared.txt", 200, "2026-01-01T00:00:00Z", "hash1", None),
    ]

    plan = plan_selective_sync(mapping, local_files, drive_files)

    assert len(plan.to_upload) == 1
    assert plan.to_upload[0].relative_path == "local_only.txt"

    assert len(plan.to_download) == 1
    assert plan.to_download[0].relative_path == "remote_only.txt"

    assert len(plan.in_sync) == 1
    assert plan.in_sync[0].relative_path == "shared.txt"
