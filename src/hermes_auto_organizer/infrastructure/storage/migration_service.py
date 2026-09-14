"""
Filesystem Migration Service Adapter.
Implements MigrationPort: handles atomic copy, safety checks, source deletion,
symbolic link creation, and rollback (adapted from ai-disk-cleaner).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
from typing import Any

from hermes_auto_organizer.domain.models import MigrationRecord

logger = logging.getLogger("hermes_auto_organizer.storage.migration_service")


class FilesystemMigrationService:
    """Performs filesystem-level directory migrations with symlinks."""

    def copy_source(self, source_path: str, destination_dir: str, name: str) -> str:
        """Copies source to destination_dir/name safely."""
        src = Path(source_path).resolve()
        dest_parent = Path(destination_dir).resolve()
        dest = dest_parent / name

        if not src.exists():
            raise FileNotFoundError(f"Source does not exist: {src}")
        if not dest_parent.exists():
            dest_parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise FileExistsError(f"Destination already exists: {dest}")

        if src.is_dir():
            shutil.copytree(src, dest, symlinks=True)
        else:
            shutil.copy2(src, dest)
        return str(dest)

    def delete_source(self, source_path: str, destination_path: str) -> None:
        """
        Deletes source only after verifying destination exists and is non-empty.
        """
        src = Path(source_path)
        dest = Path(destination_path)

        if not dest.exists():
            raise RuntimeError(f"Cannot delete source: destination does not exist ({dest})")

        # Verify destination size/files
        if dest.is_dir():
            dest_items = list(dest.iterdir())
            if not dest_items and any(src.iterdir()):
                raise RuntimeError(f"Verification failed: destination is empty ({dest})")
            shutil.rmtree(src)
        else:
            if dest.stat().st_size != src.stat().st_size:
                raise RuntimeError(f"Verification failed: file size mismatch between {src} and {dest}")
            src.unlink()

    def create_symlink(self, target_dest: str, link_source: str) -> None:
        """Creates a symlink at link_source pointing to target_dest."""
        src = Path(link_source)
        dest = Path(target_dest)

        if src.exists() and not src.is_symlink():
            raise FileExistsError(f"Cannot create symlink: source path still exists ({src})")

        if src.is_symlink():
            src.unlink()

        os.symlink(dest, src)

    def rollback_migration(self, record: MigrationRecord) -> bool:
        """
        Reverts a migration:
        1. Checks symlink at source_path and unlinks it
        2. Moves destination_path back to source_path
        """
        src = Path(record.source_path)
        dest = Path(record.destination_path)

        if not dest.exists():
            logger.error("Rollback failed: destination %s does not exist", dest)
            return False

        if src.is_symlink():
            src.unlink()
        elif src.exists():
            logger.warning("Source path %s is not a symlink but exists; skipping unlink", src)

        # Move back
        shutil.move(str(dest), str(src))
        return True
