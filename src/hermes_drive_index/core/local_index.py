"""Local drive indexing into the SQLite FTS5 index.

Allows indexing local folders directly into the same search database,
enabling unified full-text search across both Google Drive and local drives.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from typing import Any, Sequence

from .extract import chunk_text, extract_text
from .index import delete_file_from_index, init_db, migrate
from .local_scanner import LocalFile, scan_local_directory
from .models import DriveFile
from .utils import now_iso


def local_file_to_drive_file(lf: LocalFile) -> DriveFile:
    """Convert a LocalFile into a DriveFile compatible with extraction helpers."""
    return DriveFile(
        id=lf.id,
        name=lf.name,
        mime_type=lf.mime_type,
        path=lf.path,
        size=lf.size,
        modified_time=lf.modified_time,
        md5_checksum=lf.md5_checksum,
        web_view_link=lf.web_view_link,
    )


def index_local_file(
    con: sqlite3.Connection,
    lf: LocalFile,
    metrics: dict,
    *,
    ocr_pdf_enabled: bool = False,
    ocr_image_enabled: bool = False,
) -> None:
    """Index a single local file into SQLite files, chunks, and chunks_fts tables."""
    delete_file_from_index(con, lf.id)
    local_path = Path(lf.path)
    if not local_path.exists():
        return

    df = local_file_to_drive_file(lf)
    text = ""
    error = None

    try:
        text = extract_text(
            local_path,
            df,
            ocr_pdf_enabled=ocr_pdf_enabled,
            ocr_image_enabled=ocr_image_enabled,
        )
    except Exception as exc:
        error = str(exc)

    chunks = chunk_text(text) if text and text.strip() else []

    if not chunks:
        status = "indexed_metadata"
        if error is None:
            error = "no text extracted; indexed filename/path metadata only"
        metrics["files_metadata_only"] = metrics.get("files_metadata_only", 0) + 1
        chunks = [f"{lf.name}\n{lf.path}\n{lf.mime_type}"]
    else:
        status = "indexed"
        metrics["files_indexed_native"] = metrics.get("files_indexed_native", 0) + 1

    con.execute(
        "insert or replace into files values (?,?,?,?,?,?,?,?,?,?,?)",
        (
            lf.id,
            lf.name,
            lf.path,
            lf.mime_type,
            lf.size,
            lf.modified_time,
            lf.md5_checksum,
            lf.web_view_link,
            now_iso(),
            status,
            error,
        ),
    )

    for i, ch in enumerate(chunks):
        chunk_id = hashlib.sha1(f"{lf.id}:{i}".encode()).hexdigest()
        cur = con.execute(
            "insert into chunks(chunk_id,file_id,chunk_index,text,token_estimate) values (?,?,?,?,?)",
            (chunk_id, lf.id, i, ch, max(1, len(ch) // 4)),
        )
        con.execute(
            "insert into chunks_fts(rowid,text,name,path,file_id,chunk_id) values (?,?,?,?,?,?)",
            (cur.lastrowid, ch, lf.name, lf.path, lf.id, chunk_id),
        )
        metrics["chunks"] = metrics.get("chunks", 0) + 1


def index_local_directory(
    db_path: Path,
    directory_path: Path | str,
    *,
    recursive: bool = True,
    ocr_pdf_enabled: bool = False,
    ocr_image_enabled: bool = False,
    exclude_dirs: Sequence[str] = (),
) -> dict:
    """Index an entire local directory into the SQLite index database."""
    base = Path(directory_path).resolve()
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Local directory does not exist: {base}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    init_db(db_path)
    migrate(con)

    scanned_files = scan_local_directory(
        base,
        recursive=recursive,
        compute_hashes=True,
        exclude_dirs=exclude_dirs,
    )

    metrics = {
        "directory": str(base),
        "files_scanned": len(scanned_files),
        "files_indexed": 0,
        "files_metadata_only": 0,
        "files_failed": 0,
        "chunks": 0,
        "errors": [],
    }

    try:
        con.execute("begin")
        for lf in scanned_files:
            if lf.is_dir:
                continue
            try:
                index_local_file(
                    con,
                    lf,
                    metrics,
                    ocr_pdf_enabled=ocr_pdf_enabled,
                    ocr_image_enabled=ocr_image_enabled,
                )
                metrics["files_indexed"] += 1
            except Exception as exc:
                metrics["files_failed"] += 1
                metrics["errors"].append({"path": lf.path, "error": str(exc)})
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    return metrics
