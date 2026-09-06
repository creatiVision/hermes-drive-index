from __future__ import annotations

from pathlib import Path
import sqlite3

from hermes_drive_index.core.sync_state import (
    get_sync_record,
    init_sync_db,
    record_sync_success,
    remove_sync_record,
    resolve_conflict,
)


def test_sync_state_crud(tmp_path: Path):
    db_file = tmp_path / "sync_state.db"
    con = init_sync_db(db_file)

    # Initial get should be None
    assert get_sync_record(con, "work_docs", "notes/todo.txt") is None

    # Record sync success
    record_sync_success(
        con,
        "work_docs",
        "notes/todo.txt",
        local_mtime="2026-09-01T10:00:00Z",
        local_sha256="sha123",
        local_size=450,
        cloud_file_id="drive-id-123",
        cloud_mtime="2026-09-01T10:00:00Z",
        cloud_md5="md5123",
        cloud_size=450,
    )

    rec = get_sync_record(con, "work_docs", "notes/todo.txt")
    assert rec is not None
    assert rec.mapping_name == "work_docs"
    assert rec.relative_path == "notes/todo.txt"
    assert rec.cloud_file_id == "drive-id-123"
    assert rec.sync_status == "in_sync"

    # Remove record
    remove_sync_record(con, "work_docs", "notes/todo.txt")
    assert get_sync_record(con, "work_docs", "notes/todo.txt") is None


def test_resolve_conflict():
    local_p = Path("/home/user/docs/budget.xlsx")

    res_local = resolve_conflict("keep_local", local_p, "budget.xlsx")
    assert res_local["action"] == "upload"

    res_remote = resolve_conflict("keep_remote", local_p, "budget.xlsx")
    assert res_remote["action"] == "download"

    res_both = resolve_conflict("rename_both", local_p, "budget.xlsx")
    assert res_both["action"] == "rename_and_download"
    assert "budget_local_" in res_both["renamed_local"]
