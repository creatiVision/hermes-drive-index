"""
Unit tests for domain entities and value objects.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from uuid import uuid4

from hermes_auto_organizer.domain.models import (
    FileNode,
    MoveIntent,
    OperationType,
    OrganizationRule,
    RuleState,
    StorageRoot,
    StorageRootType,
    SyncStatus,
    WatchMode,
)


def test_storage_root_creation():
    root = StorageRoot(
        root_name="projects",
        root_type=StorageRootType.LOCAL_DIR,
        uri_path="/media/work-data/002_cv-projects",
        watch_mode=WatchMode.POLL,
    )
    assert root.root_name == "projects"
    assert root.is_active is True
    assert root.root_type == StorageRootType.LOCAL_DIR


def test_file_node_creation():
    root_id = uuid4()
    node = FileNode(
        root_id=root_id,
        relative_path="CAD/plan.dwg",
        physical_path="/media/work-data/002_cv-projects/CAD/plan.dwg",
        file_name="plan.dwg",
        file_extension=".dwg",
        mime_type="image/vnd.dwg",
        size_bytes=10240,
        content_sha256="abc123sha256",
        sync_status=SyncStatus.CLEAN,
    )
    assert node.file_name == "plan.dwg"
    assert node.size_bytes == 10240
    assert node.is_deleted is False


def test_organization_rule_defaults():
    rule = OrganizationRule(
        rule_name="Route CAD files",
        source_pattern="**/*.dwg",
        target_path_template="Projects/CAD/{file_name}",
    )
    assert rule.state == RuleState.DRAFT
    assert rule.dry_run_last_count == 0


def test_move_intent_creation():
    file_id = uuid4()
    intent = MoveIntent(
        file_id=file_id,
        source_path="/Downloads/test.pdf",
        destination_path="/Documents/test.pdf",
        source_sha256="hash123",
        operation_type=OperationType.LOCAL_MOVE,
        is_cross_device=False,
    )
    assert intent.operation_type == OperationType.LOCAL_MOVE
    assert intent.is_cross_device is False
