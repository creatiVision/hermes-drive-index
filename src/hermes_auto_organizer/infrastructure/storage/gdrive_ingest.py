"""
Google Drive to PostgreSQL Ingestion Service.

Streams DriveFile metadata from the Google Drive crawler directly into
PostgreSQL file_nodes using clean repository abstractions.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

from hermes_auto_organizer.application.ports.repository import NodeRepositoryPort
from hermes_auto_organizer.domain.models import (
    FileNode,
    StorageRoot,
    StorageRootType,
    SyncStatus,
    WatchMode,
)
from hermes_drive_index.core.models import DriveFile, GOOGLE_FOLDER

logger = logging.getLogger("hermes_auto_organizer.storage.gdrive_ingest")


class GDrivePostgresIngester:
    """Ingests Google Drive crawling results into PostgreSQL file_nodes."""

    def __init__(self, repo: NodeRepositoryPort) -> None:
        self._repo = repo

    async def ensure_gdrive_root(self, root_name: str = "Google Drive", uri_path: str = "gdrive://root") -> StorageRoot:
        root = StorageRoot(
            root_name=root_name,
            root_type=StorageRootType.GDRIVE_ROOT,
            uri_path=uri_path,
            watch_mode=WatchMode.POLL,
            is_active=True,
        )
        return await self._repo.upsert_root(root)

    async def ingest_drive_files(self, files: Iterable[DriveFile], root_id: UUID) -> int:
        count = 0
        now = datetime.now(timezone.utc)
        for df in files:
            # Skip folders themselves as file nodes
            if df.mime_type == GOOGLE_FOLDER:
                continue

            node_id = uuid5(NAMESPACE_URL, f"gdrive:{df.id}")
            mtime = now
            if df.modified_time:
                try:
                    mtime = datetime.fromisoformat(df.modified_time.replace("Z", "+00:00"))
                except ValueError:
                    mtime = now

            node = FileNode(
                id=node_id,
                root_id=root_id,
                relative_path=df.path.lstrip("/"),
                physical_path=f"gdrive://{df.id}",
                file_name=df.name,
                size_bytes=df.size,
                mtime=mtime,
                gdrive_id=df.id,
                file_extension=Path(df.name).suffix.lower() if df.name else None,
                mime_type=df.mime_type,
                head_tail_xxh64=df.md5_checksum[:16] if df.md5_checksum else None,
                content_sha256=None,
                sync_status=SyncStatus.CLEAN,
                last_scanned_at=now,
            )
            await self._repo.upsert_file(node)
            count += 1

        logger.info("Ingested %d Google Drive files into PostgreSQL root %s", count, root_id)
        return count
