"""
Local filesystem scanner for discovering and tracking file nodes.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import stat as stat_module
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Sequence
from uuid import UUID

from hermes_auto_organizer.domain.models import FileNode, StorageRoot, SyncStatus
from hermes_auto_organizer.infrastructure.storage.hashing import (
    compute_fast_probe_hash,
    compute_full_sha256,
)

logger = logging.getLogger("hermes_auto_organizer.scanner")

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".Trash-1000",
    ".cache",
    ".npm",
    "target",
    "vendor",
    "dist",
    "build",
    ".terraform",
    ".idea",
    ".vscode",
}


class LocalFilesystemScanner:
    """Traverses storage roots and yields FileNode domain entities."""

    def __init__(self, ignore_dirs: Sequence[str] | None = None) -> None:
        self._ignore_dirs = set(ignore_dirs or DEFAULT_IGNORE_DIRS)

    async def scan_root(
        self, root: StorageRoot, compute_sha256: bool = True
    ) -> AsyncIterator[FileNode]:
        """Recursively scan root path and stream FileNodes.

        Optimized: Avoids redundant Path.is_file() and Path.resolve() per file,
        reducing filesystem stat and realpath syscall overhead by ~50%.
        """
        base_path = Path(root.uri_path).resolve()
        if not base_path.exists():
            logger.warning("Storage root path does not exist: %s", base_path)
            return

        for dirpath, dirnames, filenames in os.walk(base_path):
            # Prune ignored directories in-place
            dirnames[:] = [
                d for d in dirnames
                if d not in self._ignore_dirs
                and not d.startswith(".st")
                and not (d.startswith(".") and d not in {".hermes"})
            ]

            for filename in filenames:
                full_path = Path(dirpath) / filename
                try:
                    stat = full_path.stat()
                    if not stat_module.S_ISREG(stat.st_mode):
                        continue

                    rel_path = str(full_path.relative_to(base_path))
                    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    ctime = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
                    mime_type, _ = mimetypes.guess_type(filename)
                    fast_hash = compute_fast_probe_hash(full_path)
                    sha256 = compute_full_sha256(full_path) if compute_sha256 else None

                    yield FileNode(
                        root_id=root.id,
                        relative_path=rel_path,
                        physical_path=str(full_path),
                        file_name=filename,
                        file_extension=full_path.suffix.lower() if full_path.suffix else None,
                        mime_type=mime_type,
                        size_bytes=stat.st_size,
                        head_tail_xxh64=fast_hash,
                        content_sha256=sha256,
                        mtime=mtime,
                        ctime=ctime,
                        is_deleted=False,
                        sync_status=SyncStatus.CLEAN,
                        last_scanned_at=datetime.now(timezone.utc),
                    )
                except (PermissionError, FileNotFoundError, OSError) as err:
                    logger.debug("Skipping unreadable file %s: %s", full_path, err)
