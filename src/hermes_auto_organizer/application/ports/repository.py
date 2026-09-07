"""
Repository port abstractions for metadata, vector search, and audit ledger.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from typing import Protocol, Sequence
from uuid import UUID

from hermes_auto_organizer.domain.models import (
    ExecutionRecord,
    FileEmbedding,
    FileExtraction,
    FileNode,
    OrganizationRule,
    RollbackState,
    RuleState,
    StorageRoot,
    StructuralAnomaly,
)


class NodeRepositoryPort(Protocol):
    """Persistence contract for storage roots and file nodes."""

    async def upsert_root(self, root: StorageRoot) -> StorageRoot:
        ...

    async def get_root_by_name(self, root_name: str) -> StorageRoot | None:
        ...

    async def list_active_roots(self) -> list[StorageRoot]:
        ...

    async def batch_upsert_nodes(self, nodes: Sequence[FileNode]) -> int:
        ...

    async def get_node_by_path(self, physical_path: str) -> FileNode | None:
        ...

    async def list_unorganized_nodes(self, limit: int = 100) -> list[FileNode]:
        ...

    async def mark_missing_nodes(self, root_id: UUID, scanned_ids: Sequence[UUID]) -> int:
        ...


class ExtractionRepositoryPort(Protocol):
    """Cache repository for content-hash summaries and vectors."""

    async def get_extraction(self, content_sha256: str) -> FileExtraction | None:
        ...

    async def save_extraction(self, extraction: FileExtraction) -> None:
        ...

    async def save_embedding(self, embedding: FileEmbedding) -> None:
        ...

    async def search_similar_vectors(
        self, query_vector: list[float], model_name: str, limit: int = 20
    ) -> list[tuple[str, float]]:
        """Return list of (content_sha256, cosine_distance)."""
        ...


class RuleRepositoryPort(Protocol):
    """Persistence contract for organization rules."""

    async def save_rule(self, rule: OrganizationRule) -> OrganizationRule:
        ...

    async def get_rule(self, rule_id: UUID) -> OrganizationRule | None:
        ...

    async def list_rules(self, state: RuleState | None = None) -> list[OrganizationRule]:
        ...

    async def update_rule_state(self, rule_id: UUID, new_state: RuleState) -> bool:
        ...


class ExecutionLedgerPort(Protocol):
    """Audit ledger for atomic operations and LIFO rollback."""

    async def append_record(self, record: ExecutionRecord) -> None:
        ...

    async def list_batch_records(self, batch_id: UUID) -> list[ExecutionRecord]:
        ...

    async def update_record_state(self, record_id: UUID, new_state: RollbackState) -> None:
        ...
