"""
Unit tests for filesystem extended attributes metadata writer and reader.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from pathlib import Path

from hermes_auto_organizer.infrastructure.storage.metadata_writer import (
    read_file_metadata,
    write_file_metadata,
)


def test_write_and_read_file_metadata(tmp_path: Path):
    test_file = tmp_path / "Rechnung_Telekom_2026.pdf"
    test_file.write_bytes(b"%PDF-1.4 test")

    summary = "Telekom Jahresabrechnung 2026 über 540,20 Euro."
    tags = ["Rechnung", "Telekom", "Steuern", "2026"]
    doc_type = "invoice"
    extra = {"amount": "540.20 EUR", "year": 2026}

    success = write_file_metadata(
        test_file,
        summary=summary,
        tags=tags,
        document_type=doc_type,
        extra_metadata=extra,
    )
    assert success is True

    # Read back metadata
    meta = read_file_metadata(test_file)
    assert meta["summary"] == summary
    assert "Rechnung" in meta["tags"]
    assert "Telekom" in meta["tags"]
    assert meta["document_type"] == "invoice"
    assert meta["meta"]["amount"] == "540.20 EUR"


def test_read_metadata_nonexistent_file(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.pdf"
    meta = read_file_metadata(non_existent)
    assert meta == {}
