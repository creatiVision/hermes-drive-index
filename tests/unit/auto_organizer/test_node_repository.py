"""
Unit tests for PostgresNodeRepository and repository ports.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime, timezone

from hermes_auto_organizer.domain.models import FileNode, SyncStatus
from hermes_auto_organizer.infrastructure.db.repositories import PostgresNodeRepository


def test_batch_upsert_nodes_empty():
    pool = MagicMock()
    repo = PostgresNodeRepository(pool)
    result = asyncio.run(repo.batch_upsert_nodes([]))
    assert result == 0
    pool.acquire.assert_not_called()


def test_batch_upsert_nodes_success():
    async def _run():
        pool = MagicMock()
        conn = AsyncMock()

        # Configure context manager for pool.acquire()
        acquire_cm = MagicMock()
        acquire_cm.__aenter__ = AsyncMock(return_value=conn)
        acquire_cm.__aexit__ = AsyncMock(return_value=None)
        pool.acquire = MagicMock(return_value=acquire_cm)

        # Configure context manager for conn.transaction()
        tx_cm = MagicMock()
        tx_cm.__aenter__ = AsyncMock(return_value=None)
        tx_cm.__aexit__ = AsyncMock(return_value=None)
        conn.transaction = MagicMock(return_value=tx_cm)

        repo = PostgresNodeRepository(pool)

        root_id = uuid.uuid4()
        node1 = FileNode(
            id=uuid.uuid4(),
            root_id=root_id,
            relative_path="file1.txt",
            physical_path="/tmp/file1.txt",
            gdrive_id=None,
            file_name="file1.txt",
            file_extension=".txt",
            mime_type="text/plain",
            size_bytes=100,
            head_tail_xxh64="12345",
            content_sha256="abcdef",
            mtime=datetime.now(timezone.utc),
            ctime=datetime.now(timezone.utc),
            is_deleted=False,
            sync_status=SyncStatus.CLEAN,
            last_scanned_at=datetime.now(timezone.utc),
        )
        node2 = FileNode(
            id=uuid.uuid4(),
            root_id=root_id,
            relative_path="file2.txt",
            physical_path="/tmp/file2.txt",
            gdrive_id=None,
            file_name="file2.txt",
            file_extension=".txt",
            mime_type="text/plain",
            size_bytes=200,
            head_tail_xxh64="67890",
            content_sha256="fedcba",
            mtime=datetime.now(timezone.utc),
            ctime=datetime.now(timezone.utc),
            is_deleted=False,
            sync_status=SyncStatus.CLEAN,
            last_scanned_at=datetime.now(timezone.utc),
        )

        count = await repo.batch_upsert_nodes([node1, node2])
        assert count == 2

        # Assert conn.executemany was called once with query and list of 2 tuples
        assert conn.executemany.call_count == 1
        args, _ = conn.executemany.call_args
        query, args_list = args
        assert "INSERT INTO file_nodes" in query
        assert len(args_list) == 2
        assert args_list[0][0] == node1.id
        assert args_list[0][2] == "file1.txt"
        assert args_list[1][0] == node2.id
        assert args_list[1][2] == "file2.txt"

    asyncio.run(_run())
