"""
Unit tests for DryRunEngine.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from pathlib import Path
from uuid import uuid4

from hermes_auto_organizer.application.use_cases.dry_run import DryRunEngine
from hermes_auto_organizer.domain.models import (
    FileNode,
    OrganizationRule,
    StorageRoot,
    StorageRootType,
    SyncStatus,
    WatchMode,
)


def test_dry_run_simulation_and_collision(tmp_path: Path):
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Pre-create an existing file to trigger collision
    existing = target_dir / "Plans" / "2026" / "floor_plan.dwg"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing content", encoding="utf-8")

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "floor_plan.dwg"
    source_file.write_text("new content", encoding="utf-8")

    root = StorageRoot(
        root_name="target_root",
        root_type=StorageRootType.LOCAL_DIR,
        uri_path=str(target_dir),
        watch_mode=WatchMode.POLL,
    )

    rule = OrganizationRule(
        rule_name="Organize CAD Plans",
        source_pattern="*.dwg",
        target_path_template="Plans/{year}/{file_name}",
        condition_json={"extensions": [".dwg"]},
    )

    node = FileNode(
        root_id=uuid4(),
        relative_path="floor_plan.dwg",
        physical_path=str(source_file),
        file_name="floor_plan.dwg",
        file_extension=".dwg",
        content_sha256="newhash999",
        size_bytes=len("new content"),
        sync_status=SyncStatus.CLEAN,
    )

    intents = DryRunEngine.simulate_rule(rule, [node], root)

    assert len(intents) == 1
    intent = intents[0]
    assert intent.requires_collision_rename is True
    assert "_conflict_" in intent.destination_path
    assert intent.destination_path.endswith(".dwg")
