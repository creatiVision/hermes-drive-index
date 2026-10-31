"""Tests for SymlinkMigratorUseCase and FilesystemMigrationService."""

import os
from pathlib import Path
import pytest

from hermes_auto_organizer.application.use_cases.symlink_migrator import SymlinkMigratorUseCase
from hermes_auto_organizer.domain.models import MigrationStatus
from hermes_auto_organizer.infrastructure.storage.migration_service import FilesystemMigrationService


def test_migration_and_rollback(tmp_path: Path):
    # Setup source directory with files
    source_dir = tmp_path / "source_models"
    source_dir.mkdir()
    (source_dir / "weights.bin").write_bytes(b"dummy model weights data")
    (source_dir / "config.json").write_text('{"vocab_size": 32000}')

    dest_root = tmp_path / "destination_drive"
    dest_root.mkdir()

    service = FilesystemMigrationService()
    use_case = SymlinkMigratorUseCase(service)

    # Migrate
    record = use_case.migrate(str(source_dir), str(dest_root), name="migrated_models")
    assert record.status == MigrationStatus.ACTIVE
    assert record.symlink_created is True
    assert record.size_bytes > 0

    # Verify source is now a symlink pointing to destination
    assert source_dir.is_symlink()
    assert (source_dir / "weights.bin").read_bytes() == b"dummy model weights data"

    # Destination contains the actual directory
    migrated_dest = dest_root / "migrated_models"
    assert migrated_dest.is_dir()
    assert not migrated_dest.is_symlink()

    # Rollback
    reverted_record = use_case.rollback(record)
    assert reverted_record.status == MigrationStatus.REVERTED
    assert not source_dir.is_symlink()
    assert source_dir.is_dir()
    assert (source_dir / "weights.bin").read_bytes() == b"dummy model weights data"
    assert not migrated_dest.exists()
