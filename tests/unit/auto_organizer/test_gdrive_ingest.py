"""
Unit tests for Google Drive to PostgreSQL Ingestion Bridge.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from hermes_auto_organizer.domain.models import StorageRoot, StorageRootType
from hermes_auto_organizer.infrastructure.storage.gdrive_ingest import GDrivePostgresIngester
from hermes_drive_index.core.models import DriveFile, GOOGLE_DOC, GOOGLE_FOLDER


def test_gdrive_postgres_ingester():
    mock_repo = AsyncMock()
    mock_root = StorageRoot(id=uuid4(), root_name="Google Drive", root_type=StorageRootType.GDRIVE_ROOT)
    mock_repo.upsert_root.return_value = mock_root
    mock_repo.upsert_file.return_value = None

    ingester = GDrivePostgresIngester(mock_repo)

    root = asyncio.run(ingester.ensure_gdrive_root())
    assert root.root_name == "Google Drive"

    files = [
        DriveFile(
            id="folder_1",
            name="Documents",
            mime_type=GOOGLE_FOLDER,
            path="/Documents",
            size=0,
            modified_time=None,
            md5_checksum=None,
            web_view_link=None,
            parents=(),
        ),
        DriveFile(
            id="doc_1",
            name="Annual_Report_2026.docx",
            mime_type=GOOGLE_DOC,
            path="/Documents/Annual_Report_2026.docx",
            size=102400,
            modified_time="2026-05-10T14:30:00.000Z",
            md5_checksum="d41d8cd98f00b204e9800998ecf8427e",
            web_view_link="https://drive.google.com/open?id=doc_1",
            parents=("folder_1",),
        ),
    ]

    count = asyncio.run(ingester.ingest_drive_files(files, root.id))
    # Folders should be skipped, only the file is ingested
    assert count == 1
    assert mock_repo.upsert_file.call_count == 1

    called_node = mock_repo.upsert_file.call_args[0][0]
    assert called_node.gdrive_id == "doc_1"
    assert called_node.file_name == "Annual_Report_2026.docx"
    assert called_node.relative_path == "Documents/Annual_Report_2026.docx"
    assert called_node.size_bytes == 102400
    assert called_node.file_extension == ".docx"
