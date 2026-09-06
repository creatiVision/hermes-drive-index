"""SQLite-backed sync state tracking and conflict resolution.

Maintains persistent synchronization state for selective sync mappings,
recording hashes, timestamps, and detection of local vs remote additions,
modifications, deletions, and conflicts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Sequence

from .utils import now_iso


@dataclass
class FileSyncRecord:
    mapping_name: str
    relative_path: str
    local_mtime: str | None
    local_sha256: str | None
    local_size: int
    cloud_file_id: str | None
    cloud_mtime: str | None
    cloud_md5: str | None
    cloud_size: int
    sync_status: str  # in_sync, local_newer, cloud_newer, conflict, local_deleted, cloud_deleted
    last_synced_at: str


def init_sync_db(db_path: Path | str) -> sqlite3.Connection:
    """Initialize or upgrade sync state tables in SQLite database."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        create table if not exists sync_records (
            mapping_name text,
            relative_path text,
            local_mtime text,
            local_sha256 text,
            local_size integer,
            cloud_file_id text,
            cloud_mtime text,
            cloud_md5 text,
            cloud_size integer,
            sync_status text,
            last_synced_at text,
            primary key (mapping_name, relative_path)
        );

        create table if not exists sync_history (
            id integer primary key autoincrement,
            mapping_name text,
            action text,
            relative_path text,
            detail text,
            timestamp text
        );
        """
    )
    con.commit()
    return con


def get_sync_record(con: sqlite3.Connection, mapping_name: str, relative_path: str) -> FileSyncRecord | None:
    """Retrieve existing sync record for a relative path in a mapping."""
    row = con.execute(
        "select * from sync_records where mapping_name = ? and relative_path = ?",
        (mapping_name, relative_path),
    ).fetchone()
    if not row:
        return None
    return FileSyncRecord(
        mapping_name=row["mapping_name"],
        relative_path=row["relative_path"],
        local_mtime=row["local_mtime"],
        local_sha256=row["local_sha256"],
        local_size=row["local_size"] or 0,
        cloud_file_id=row["cloud_file_id"],
        cloud_mtime=row["cloud_mtime"],
        cloud_md5=row["cloud_md5"],
        cloud_size=row["cloud_size"] or 0,
        sync_status=row["sync_status"],
        last_synced_at=row["last_synced_at"],
    )


def record_sync_success(
    con: sqlite3.Connection,
    mapping_name: str,
    relative_path: str,
    *,
    local_mtime: str | None,
    local_sha256: str | None,
    local_size: int,
    cloud_file_id: str | None,
    cloud_mtime: str | None,
    cloud_md5: str | None,
    cloud_size: int,
) -> None:
    """Update or insert sync record upon successful file transfer."""
    synced_at = now_iso()
    con.execute(
        """
        insert or replace into sync_records (
            mapping_name, relative_path, local_mtime, local_sha256, local_size,
            cloud_file_id, cloud_mtime, cloud_md5, cloud_size, sync_status, last_synced_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_sync', ?)
        """,
        (
            mapping_name,
            relative_path,
            local_mtime,
            local_sha256,
            local_size,
            cloud_file_id,
            cloud_mtime,
            cloud_md5,
            cloud_size,
            synced_at,
        ),
    )
    con.execute(
        "insert into sync_history (mapping_name, action, relative_path, detail, timestamp) values (?, 'synced', ?, 'file in sync', ?)",
        (mapping_name, relative_path, synced_at),
    )
    con.commit()


def remove_sync_record(con: sqlite3.Connection, mapping_name: str, relative_path: str) -> None:
    """Remove a sync record when a file is permanently removed from sync scope."""
    con.execute(
        "delete from sync_records where mapping_name = ? and relative_path = ?",
        (mapping_name, relative_path),
    )
    con.execute(
        "insert into sync_history (mapping_name, action, relative_path, detail, timestamp) values (?, 'deleted', ?, 'record deleted', ?)",
        (mapping_name, relative_path, now_iso()),
    )
    con.commit()


def resolve_conflict(
    strategy: str,  # "keep_local", "keep_remote", "rename_both"
    local_path: Path,
    remote_name: str,
) -> dict:
    """Determine file action based on conflict resolution strategy."""
    if strategy == "keep_local":
        return {"action": "upload", "target": local_path.name, "reason": "Conflict resolved by keeping local version"}
    elif strategy == "keep_remote":
        return {"action": "download", "target": local_path.name, "reason": "Conflict resolved by keeping remote version"}
    else:  # rename_both or rename_conflict
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        stem = local_path.stem
        ext = local_path.suffix
        renamed_local = f"{stem}_local_{timestamp}{ext}"
        return {
            "action": "rename_and_download",
            "renamed_local": renamed_local,
            "reason": "Conflict preserved: local renamed, cloud downloaded",
        }
