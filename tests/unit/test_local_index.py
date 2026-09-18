from __future__ import annotations

from pathlib import Path
import sqlite3
from unittest.mock import patch

from hermes_drive_index.core.index import init_db, migrate
from hermes_drive_index.core.local_index import index_local_directory, index_local_file
from hermes_drive_index.core.local_scanner import LocalFile
from hermes_drive_index.core.search import search_db


def test_index_local_directory_and_search(tmp_path: Path):
    db_path = tmp_path / "index.db"
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir()

    (docs_dir / "confidential_memo.txt").write_text("This is an internal memo regarding Project Phoenix and quarterly earnings.")
    (docs_dir / "invoice.txt").write_text("Invoice 1042 for consultation services.")

    metrics = index_local_directory(db_path, docs_dir)
    assert metrics["files_scanned"] == 2
    assert metrics["files_indexed"] == 2
    assert metrics["chunks"] >= 2

    # Query the local SQLite index
    res = search_db(db_path, "Phoenix")
    assert len(res["results"]) == 1
    assert "confidential_memo.txt" in res["results"][0]["name"]
    assert "Phoenix" in res["results"][0]["snippet"]


def test_index_local_file_non_existent(tmp_path: Path):
    db_path = tmp_path / "index.db"
    con = init_db(db_path)
    migrate(con)

    lf = LocalFile(
        id="local:nonexistent.txt",
        name="nonexistent.txt",
        path=str(tmp_path / "nonexistent.txt"),
        mime_type="text/plain",
        size=100,
        modified_time="2025-01-01T00:00:00Z",
        md5_checksum="d41d8cd98f00b204e9800998ecf8427e",
    )
    metrics = {}
    index_local_file(con, lf, metrics)

    rows = con.execute("select * from files").fetchall()
    assert len(rows) == 0
    con.close()


def test_index_local_file_success(tmp_path: Path):
    db_path = tmp_path / "index.db"
    con = init_db(db_path)
    migrate(con)

    fpath = tmp_path / "test.txt"
    fpath.write_text("Hello Hermes Drive Index!")

    lf = LocalFile(
        id="local:test.txt",
        name="test.txt",
        path=str(fpath),
        mime_type="text/plain",
        size=fpath.stat().st_size,
        modified_time="2025-01-01T00:00:00Z",
        md5_checksum="checksum123",
    )
    metrics = {}
    index_local_file(con, lf, metrics, ocr_pdf_enabled=True, ocr_image_enabled=False)

    assert metrics.get("files_indexed_native") == 1
    assert metrics.get("chunks") == 1

    file_row = con.execute("select * from files where file_id=?", (lf.id,)).fetchone()
    assert file_row is not None
    assert file_row[9] == "indexed"  # status

    chunks = con.execute("select * from chunks where file_id=?", (lf.id,)).fetchall()
    assert len(chunks) == 1
    assert "Hello Hermes" in chunks[0][3]  # text
    con.close()


def test_index_local_file_empty_text_metadata_only(tmp_path: Path):
    db_path = tmp_path / "index.db"
    con = init_db(db_path)
    migrate(con)

    fpath = tmp_path / "empty.bin"
    fpath.write_bytes(b"")

    lf = LocalFile(
        id="local:empty.bin",
        name="empty.bin",
        path=str(fpath),
        mime_type="application/octet-stream",
        size=0,
        modified_time="2025-01-01T00:00:00Z",
        md5_checksum="checksumempty",
    )
    metrics = {}
    index_local_file(con, lf, metrics)

    assert metrics.get("files_metadata_only") == 1
    assert metrics.get("chunks") == 1

    file_row = con.execute("select * from files where file_id=?", (lf.id,)).fetchone()
    assert file_row is not None
    assert file_row[9] == "indexed_metadata"  # status
    assert file_row[10] == "no text extracted; indexed filename/path metadata only"  # error

    chunks = con.execute("select * from chunks where file_id=?", (lf.id,)).fetchall()
    assert len(chunks) == 1
    assert "empty.bin" in chunks[0][3]
    con.close()


def test_index_local_file_extraction_exception(tmp_path: Path):
    db_path = tmp_path / "index.db"
    con = init_db(db_path)
    migrate(con)

    fpath = tmp_path / "corrupt.pdf"
    fpath.write_text("corrupt content")

    lf = LocalFile(
        id="local:corrupt.pdf",
        name="corrupt.pdf",
        path=str(fpath),
        mime_type="application/pdf",
        size=10,
        modified_time="2025-01-01T00:00:00Z",
        md5_checksum="checksumcorrupt",
    )
    metrics = {}

    with patch("hermes_drive_index.core.local_index.extract_text", side_effect=RuntimeError("Extraction failed")):
        index_local_file(con, lf, metrics, ocr_pdf_enabled=True)

    assert metrics.get("files_metadata_only") == 1
    assert metrics.get("chunks") == 1

    file_row = con.execute("select * from files where file_id=?", (lf.id,)).fetchone()
    assert file_row is not None
    assert file_row[9] == "indexed_metadata"
    assert file_row[10] == "Extraction failed"
    con.close()


def test_index_local_file_reindexing_cleans_old_entry(tmp_path: Path):
    db_path = tmp_path / "index.db"
    con = init_db(db_path)
    migrate(con)

    fpath = tmp_path / "file.txt"
    fpath.write_text("Version 1")

    lf = LocalFile(
        id="local:file.txt",
        name="file.txt",
        path=str(fpath),
        mime_type="text/plain",
        size=9,
        modified_time="2025-01-01T00:00:00Z",
        md5_checksum="v1",
    )
    metrics1 = {}
    index_local_file(con, lf, metrics1)

    fpath.write_text("Version 2 updated content")
    metrics2 = {}
    index_local_file(con, lf, metrics2)

    files = con.execute("select * from files where file_id=?", (lf.id,)).fetchall()
    assert len(files) == 1

    chunks = con.execute("select * from chunks where file_id=?", (lf.id,)).fetchall()
    assert len(chunks) == 1
    assert "Version 2" in chunks[0][3]
    con.close()
