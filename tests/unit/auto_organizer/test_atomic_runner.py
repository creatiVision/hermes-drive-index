"""
Unit tests for AtomicExecutionRunner and rollback.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from pathlib import Path
from uuid import uuid4

from hermes_auto_organizer.domain.models import MoveIntent, OperationType, RollbackState
from hermes_auto_organizer.infrastructure.storage.atomic_runner import AtomicExecutionRunner
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256


def test_atomic_move_and_rollback(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "document.txt"
    source_file.write_text("Mission critical content", encoding="utf-8")
    original_hash = compute_full_sha256(source_file)

    target_dir = tmp_path / "target"
    dest_file = target_dir / "archive" / "document.txt"

    intent = MoveIntent(
        file_id=uuid4(),
        source_path=str(source_file),
        destination_path=str(dest_file),
        source_sha256=original_hash,
        operation_type=OperationType.LOCAL_MOVE,
    )

    batch_id = uuid4()
    # 1. Execute move
    record = AtomicExecutionRunner.execute_move(intent, batch_id)

    assert record.rollback_state == RollbackState.EXECUTED
    assert not source_file.exists()
    assert dest_file.exists()
    assert compute_full_sha256(dest_file) == original_hash

    # 2. Rollback move
    rollback_ok = AtomicExecutionRunner.rollback_move(record)

    assert rollback_ok is True
    assert source_file.exists()
    assert not dest_file.exists()
    assert compute_full_sha256(source_file) == original_hash

from hermes_auto_organizer.infrastructure.storage.metadata_writer import read_file_metadata


def test_atomic_move_carries_metadata(tmp_path: Path):
    source_dir = tmp_path / "downloads"
    source_dir.mkdir()
    source_file = source_dir / "invoice.pdf"
    source_file.write_bytes(b"%PDF-1.4 test invoice")
    orig_hash = compute_full_sha256(source_file)

    dest_file = tmp_path / "archive" / "2026" / "invoice.pdf"

    intent = MoveIntent(
        file_id=uuid4(),
        source_path=str(source_file),
        destination_path=str(dest_file),
        source_sha256=orig_hash,
        operation_type=OperationType.LOCAL_MOVE,
        metadata={
            "summary": "AI Zusammenfassung: Rechnung 2026",
            "tags": ["Rechnung", "Steuern", "2026"],
            "document_type": "invoice",
        },
    )

    record = AtomicExecutionRunner.execute_move(intent, uuid4())
    assert dest_file.exists()

    meta = read_file_metadata(dest_file)
    assert meta["summary"] == "AI Zusammenfassung: Rechnung 2026"
    assert "Rechnung" in meta["tags"]
    assert meta["document_type"] == "invoice"
