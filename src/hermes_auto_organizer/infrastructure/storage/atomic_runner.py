"""
Atomic execution runner and LIFO rollback engine.
Enforces zero-data-loss, trash safety, and cross-device EXDEV copy-verify-trash.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

try:
    from send2trash import send2trash
    _HAS_SEND2TRASH = True
except ImportError:
    _HAS_SEND2TRASH = False

from hermes_auto_organizer.domain.models import (
    ExecutionRecord,
    MoveIntent,
    OperationType,
    RollbackState,
)
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256
from hermes_auto_organizer.infrastructure.storage.metadata_writer import write_file_metadata

logger = logging.getLogger("hermes_auto_organizer.runner")


class ExecutionError(RuntimeError):
    """Raised when an atomic execution operation fails."""


class AtomicExecutionRunner:
    """Safely relocates files and logs transactional entries."""

    @classmethod
    def execute_move(cls, intent: MoveIntent, batch_id: UUID) -> ExecutionRecord:
        source = Path(intent.source_path)
        destination = Path(intent.destination_path)

        if not source.exists():
            raise ExecutionError(f"Source file does not exist: {source}")

        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # 1. Compute pre-move hash
        source_hash = compute_full_sha256(source)
        if intent.source_sha256 and source_hash != intent.source_sha256:
            raise ExecutionError(
                f"Source hash mismatch prior to move: expected {intent.source_sha256}, got {source_hash}"
            )

        # 2. Perform relocation
        if intent.is_cross_device or intent.operation_type == OperationType.CROSS_FS_COPY_DELETE:
            cls._execute_cross_device_copy_trash(source, destination, source_hash)
        else:
            cls._execute_local_move(source, destination)

        # 3. Verify destination integrity
        dest_hash = compute_full_sha256(destination)
        if dest_hash != source_hash:
            raise ExecutionError(
                f"Destination hash mismatch post-transfer: expected {source_hash}, got {dest_hash}"
            )

        # 4. Carry over and attach AI metadata (tags, summary, document_type) via xattr
        if intent.metadata:
            write_file_metadata(
                destination,
                summary=intent.metadata.get("summary"),
                tags=intent.metadata.get("tags") or intent.metadata.get("keywords"),
                document_type=intent.metadata.get("document_type"),
                extra_metadata=intent.metadata.get("extra"),
            )

        return ExecutionRecord(
            id=uuid4(),
            batch_id=batch_id,
            rule_id=intent.rule_id,
            file_id=intent.file_id,
            source_path=str(source.resolve()),
            destination_path=str(destination.resolve()),
            source_sha256=source_hash,
            operation_type=intent.operation_type,
            rollback_state=RollbackState.EXECUTED,
            executed_at=datetime.now(timezone.utc),
        )

    @classmethod
    def rollback_move(cls, record: ExecutionRecord) -> bool:
        """Reverse an executed move record, restoring the source file."""
        source = Path(record.source_path)
        destination = Path(record.destination_path)

        if not destination.exists():
            logger.error("Cannot rollback: destination file not found: %s", destination)
            return False

        # Verify destination hash matches recorded source hash
        current_dest_hash = compute_full_sha256(destination)
        if current_dest_hash != record.source_sha256:
            logger.error(
                "Cannot rollback: file at destination has been modified since execution (Hash mismatch)"
            )
            return False

        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destination), str(source))
        logger.info("Rollback successful: restored %s to %s", destination, source)
        return True

    @classmethod
    def _execute_local_move(cls, source: Path, destination: Path) -> None:
        try:
            shutil.move(str(source), str(destination))
        except OSError as e:
            if e.errno == 18:  # EXDEV: Invalid cross-device link
                source_hash = compute_full_sha256(source)
                cls._execute_cross_device_copy_trash(source, destination, source_hash)
            else:
                raise

    @classmethod
    def _execute_cross_device_copy_trash(cls, source: Path, destination: Path, expected_hash: str) -> None:
        """Atomic copy to temp file, verify hash, rename, and trash source."""
        temp_dest = destination.parent / f"{destination.name}.tmp.{uuid4().hex[:8]}"
        try:
            shutil.copy2(str(source), str(temp_dest))
            temp_hash = compute_full_sha256(temp_dest)
            if temp_hash != expected_hash:
                raise ExecutionError("Temp file copy corrupted: hash mismatch")

            temp_dest.replace(destination)

            # Move original source to trash
            if _HAS_SEND2TRASH:
                send2trash(str(source))
            else:
                trash_dir = source.parent / ".Trash"
                trash_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(trash_dir / source.name))
        except Exception:
            if temp_dest.exists():
                temp_dest.unlink(missing_ok=True)
            raise
