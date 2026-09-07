"""
Unit tests for Obsidian vault visualizer.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

from hermes_auto_organizer.domain.models import (
    AnomalyStatus,
    AnomalyType,
    MoveIntent,
    OperationType,
    StorageRoot,
    StorageRootType,
    StructuralAnomaly,
    WatchMode,
)
from hermes_auto_organizer.infrastructure.obsidian.vault_sync import ObsidianVaultVisualizer


def test_write_overview_report(tmp_path: Path):
    visualizer = ObsidianVaultVisualizer(tmp_path)
    roots = [
        StorageRoot(
            root_name="test_storage",
            root_type=StorageRootType.LOCAL_DIR,
            uri_path=str(tmp_path / "storage"),
            watch_mode=WatchMode.POLL,
        )
    ]
    anomalies = [
        StructuralAnomaly(
            file_id=uuid4(),
            anomaly_type=AnomalyType.DUMP_ZONE,
            confidence=0.95,
            explanation="Unorganized downloads",
            recommended_action="Move to Projects",
            status=AnomalyStatus.OPEN,
        )
    ]

    path = asyncio.run(visualizer.write_overview_report(roots, total_files=42, anomalies=anomalies))
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Storage Now-State Overview" in content
    assert "test_storage" in content
    assert "Unorganized downloads" in content


def test_write_pending_manifest(tmp_path: Path):
    visualizer = ObsidianVaultVisualizer(tmp_path)
    intents = [
        MoveIntent(
            file_id=uuid4(),
            source_path="/Downloads/doc.pdf",
            destination_path="/Projects/doc.pdf",
            source_sha256="1234567890abcdef",
            operation_type=OperationType.LOCAL_MOVE,
            requires_collision_rename=False,
        )
    ]

    path = asyncio.run(visualizer.write_pending_manifest("batch-9999", intents))
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Pending Moves Manifest" in content
    assert "- [ ] **MOVE**: `/Downloads/doc.pdf` ➔ `/Projects/doc.pdf`" in content
