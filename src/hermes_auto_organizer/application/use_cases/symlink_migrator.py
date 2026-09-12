"""
Symlink Migrator Use Case.
Orchestrates moving large directories across storage drives while maintaining
symbolic links, tracking migrations, and providing 1-click rollback
(adapted from ai-disk-cleaner).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from hermes_auto_organizer.application.ports.disk_analyzer_port import MigrationPort
from hermes_auto_organizer.domain.models import MigrationRecord, MigrationStatus
from hermes_auto_organizer.domain.policies import DiskCleaningPolicy, PolicyViolationError

logger = logging.getLogger("hermes_auto_organizer.use_cases.symlink_migrator")


class SymlinkMigratorUseCase:
    """Coordinates atomic directory migration and symlink management."""

    def __init__(self, migration_adapter: MigrationPort) -> None:
        self._adapter = migration_adapter

    def migrate(self, source_path: str, destination_dir: str, name: str | None = None) -> MigrationRecord:
        """
        Executes a safe directory migration:
        1. Validates source and destination safety
        2. Copies source to destination_dir/name
        3. Verifies copy and deletes source
        4. Creates symlink at source pointing to destination
        5. Returns MigrationRecord
        """
        src = DiskCleaningPolicy.normalize_path(source_path)
        dest_dir = DiskCleaningPolicy.normalize_path(destination_dir)

        if not src or not Path(src).is_dir():
            raise FileNotFoundError(f"Source directory does not exist or is not a directory: {source_path}")
        if not dest_dir or not Path(dest_dir).is_dir():
            raise FileNotFoundError(f"Destination root directory does not exist: {destination_dir}")

        DiskCleaningPolicy.assert_cleanup_safe(src)

        # Check that we are not migrating into the source itself
        if DiskCleaningPolicy.is_path_inside(dest_dir, src):
            raise PolicyViolationError(f"Destination directory cannot be inside source: {dest_dir}")

        resolved_name = name or Path(src).name
        target_dest = str(Path(dest_dir) / resolved_name)

        if Path(target_dest).exists():
            raise FileExistsError(f"Target destination already exists: {target_dest}")

        # Step 1: Copy
        logger.info("Migrating '%s' -> '%s'...", src, target_dest)
        dest_path = self._adapter.copy_source(src, dest_dir, resolved_name)

        # Step 2: Delete source (after verification)
        self._adapter.delete_source(src, dest_path)

        # Step 3: Create symlink
        self._adapter.create_symlink(dest_path, src)

        # Calculate migrated size
        size_bytes = 0
        try:
            size_bytes = sum(f.stat().st_size for f in Path(dest_path).rglob("*") if f.is_file())
        except Exception:
            pass

        record = MigrationRecord(
            source_path=src,
            destination_path=dest_path,
            size_bytes=size_bytes,
            symlink_created=True,
            status=MigrationStatus.ACTIVE,
        )
        logger.info("Migration successful: %s -> %s (%d bytes)", src, dest_path, size_bytes)
        return record

    def rollback(self, record: MigrationRecord) -> MigrationRecord:
        """Reverts a migration: removes symlink and restores directory to original source."""
        if record.status != MigrationStatus.ACTIVE:
            raise ValueError(f"Cannot rollback migration with status: {record.status.value}")

        logger.info("Rolling back migration: '%s' <- '%s'...", record.source_path, record.destination_path)
        success = self._adapter.rollback_migration(record)
        if not success:
            raise RuntimeError(f"Rollback failed for migration {record.id}")

        return MigrationRecord(
            id=record.id,
            source_path=record.source_path,
            destination_path=record.destination_path,
            size_bytes=record.size_bytes,
            symlink_created=False,
            status=MigrationStatus.REVERTED,
            created_at=record.created_at,
        )
