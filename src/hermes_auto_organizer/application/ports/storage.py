"""
Storage backend port abstraction.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol
from uuid import UUID

from hermes_auto_organizer.domain.models import ExecutionRecord, FileNode, MoveIntent, StorageRoot


class StorageBackendPort(Protocol):
    """Contract for underlying physical or cloud storage backends."""

    async def scan_root(self, root: StorageRoot) -> AsyncIterator[FileNode]:
        """Traverse and discover all files under a storage root."""
        ...

    async def execute_move(self, intent: MoveIntent, batch_id: UUID) -> ExecutionRecord:
        """Execute a move intent atomically and return an audit log record."""
        ...

    async def revert_move(self, record: ExecutionRecord) -> bool:
        """Revert a previously executed move record to restore source file."""
        ...
