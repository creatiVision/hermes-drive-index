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
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

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

        Optimized: Uses os.scandir traversal with cached DirEntry attributes and direct
        string path operations to eliminate redundant Path allocations, stat syscalls,
        and realpath resolution overhead.
        """
        base_path = Path(root.uri_path).resolve()
        if not base_path.exists():
            logger.warning("Storage root path does not exist: %s", base_path)
            return

        base_path_str = str(base_path)
        base_len = len(base_path_str) if base_path_str.endswith(os.sep) else len(base_path_str) + 1

        stack = [base_path_str]
        while stack:
            current_dir = stack.pop()
            try:
                with os.scandir(current_dir) as it:
                    entries = sorted(it, key=lambda e: e.name)
            except (PermissionError, FileNotFoundError, OSError) as err:
                logger.debug("Skipping unreadable directory %s: %s", current_dir, err)
                continue

            for entry in entries:
                try:
                    name = entry.name
                    if entry.is_dir(follow_symlinks=False):
                        if (
                            name in self._ignore_dirs
                            or name.startswith(".st")
                            or (name.startswith(".") and name != ".hermes")
                        ):
                            continue
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        stat = entry.stat(follow_symlinks=False)
                        physical_path = entry.path
                        rel_path = (
                            physical_path[base_len:]
                            if len(physical_path) > base_len
                            else name
                        )
                        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                        ctime = datetime.fromtimestamp(stat.st_ctime, tz=UTC)
                        mime_type, _ = mimetypes.guess_type(name)
                        fast_hash = compute_fast_probe_hash(physical_path)
                        sha256 = (
                            compute_full_sha256(physical_path)
                            if compute_sha256
                            else None
                        )

                        ext_idx = name.rfind(".")
                        ext = name[ext_idx:].lower() if ext_idx > 0 else None

                        yield FileNode(
                            root_id=root.id,
                            relative_path=rel_path,
                            physical_path=physical_path,
                            file_name=name,
                            file_extension=ext,
                            mime_type=mime_type,
                            size_bytes=stat.st_size,
                            head_tail_xxh64=fast_hash,
                            content_sha256=sha256,
                            mtime=mtime,
                            ctime=ctime,
                            is_deleted=False,
                            sync_status=SyncStatus.CLEAN,
                            last_scanned_at=datetime.now(UTC),
                        )
                except (PermissionError, FileNotFoundError, OSError) as err:
                    logger.debug("Skipping unreadable file %s: %s", entry.path, err)
