from __future__ import annotations

from pathlib import Path
import sqlite3

from hermes_drive_index.core.local_index import index_local_directory
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
