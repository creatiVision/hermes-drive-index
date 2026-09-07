"""
PostgreSQL and pgvector implementations of repository ports.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import json
from typing import Sequence
from uuid import UUID

import asyncpg

from hermes_auto_organizer.domain.models import (
    ExecutionRecord,
    FileEmbedding,
    FileExtraction,
    FileNode,
    OperationType,
    OrganizationRule,
    RollbackState,
    RuleState,
    StorageRoot,
    StorageRootType,
    SyncStatus,
    WatchMode,
)
from hermes_auto_organizer.infrastructure.db.connection import DatabaseConnectionPool


class PostgresNodeRepository:
    """PostgreSQL implementation of NodeRepositoryPort."""

    def __init__(self, pool: DatabaseConnectionPool) -> None:
        self._pool = pool

    async def upsert_root(self, root: StorageRoot) -> StorageRoot:
        query = """
        INSERT INTO storage_roots (id, root_name, root_type, uri_path, watch_mode, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (root_name) DO UPDATE SET
            uri_path = EXCLUDED.uri_path,
            watch_mode = EXCLUDED.watch_mode,
            is_active = EXCLUDED.is_active,
            updated_at = NOW()
        RETURNING id, root_name, root_type, uri_path, watch_mode, is_active, created_at, updated_at;
        """
        row = await self._pool.fetchrow(
            query,
            root.id,
            root.root_name,
            root.root_type.value,
            root.uri_path,
            root.watch_mode.value,
            root.is_active,
            root.created_at,
            root.updated_at,
        )
        assert row is not None
        return StorageRoot(
            id=row["id"],
            root_name=row["root_name"],
            root_type=StorageRootType(row["root_type"]),
            uri_path=row["uri_path"],
            watch_mode=WatchMode(row["watch_mode"]),
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_root_by_name(self, root_name: str) -> StorageRoot | None:
        query = "SELECT * FROM storage_roots WHERE root_name = $1 AND is_active = TRUE;"
        row = await self._pool.fetchrow(query, root_name)
        if row is None:
            return None
        return StorageRoot(
            id=row["id"],
            root_name=row["root_name"],
            root_type=StorageRootType(row["root_type"]),
            uri_path=row["uri_path"],
            watch_mode=WatchMode(row["watch_mode"]),
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def list_active_roots(self) -> list[StorageRoot]:
        query = "SELECT * FROM storage_roots WHERE is_active = TRUE ORDER BY root_name;"
        rows = await self._pool.fetch(query)
        return [
            StorageRoot(
                id=r["id"],
                root_name=r["root_name"],
                root_type=StorageRootType(r["root_type"]),
                uri_path=r["uri_path"],
                watch_mode=WatchMode(r["watch_mode"]),
                is_active=r["is_active"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def batch_upsert_nodes(self, nodes: Sequence[FileNode]) -> int:
        if not nodes:
            return 0

        query = """
        INSERT INTO file_nodes (
            id, root_id, relative_path, physical_path, gdrive_id, file_name,
            file_extension, mime_type, size_bytes, head_tail_xxh64, content_sha256,
            mtime, ctime, is_deleted, sync_status, last_scanned_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
        ) ON CONFLICT (root_id, relative_path) DO UPDATE SET
            physical_path = EXCLUDED.physical_path,
            file_name = EXCLUDED.file_name,
            size_bytes = EXCLUDED.size_bytes,
            head_tail_xxh64 = EXCLUDED.head_tail_xxh64,
            content_sha256 = EXCLUDED.content_sha256,
            mtime = EXCLUDED.mtime,
            is_deleted = FALSE,
            sync_status = EXCLUDED.sync_status,
            last_scanned_at = NOW();
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for node in nodes:
                    await conn.execute(
                        query,
                        node.id,
                        node.root_id,
                        node.relative_path,
                        node.physical_path,
                        node.gdrive_id,
                        node.file_name,
                        node.file_extension,
                        node.mime_type,
                        node.size_bytes,
                        node.head_tail_xxh64,
                        node.content_sha256,
                        node.mtime,
                        node.ctime,
                        node.is_deleted,
                        node.sync_status.value,
                        node.last_scanned_at,
                    )
        return len(nodes)

    async def get_node_by_path(self, physical_path: str) -> FileNode | None:
        query = "SELECT * FROM file_nodes WHERE physical_path = $1 AND is_deleted = FALSE;"
        row = await self._pool.fetchrow(query, physical_path)
        if row is None:
            return None
        return self._row_to_file_node(row)

    async def list_unorganized_nodes(self, limit: int = 100) -> list[FileNode]:
        query = """
        SELECT * FROM file_nodes 
        WHERE is_deleted = FALSE 
        ORDER BY last_scanned_at DESC 
        LIMIT $1;
        """
        rows = await self._pool.fetch(query, limit)
        return [self._row_to_file_node(r) for r in rows]

    async def mark_missing_nodes(self, root_id: UUID, scanned_ids: Sequence[UUID]) -> int:
        if not scanned_ids:
            return 0
        query = """
        UPDATE file_nodes 
        SET is_deleted = TRUE, sync_status = 'missing' 
        WHERE root_id = $1 AND id != ALL($2::uuid[]) AND is_deleted = FALSE;
        """
        res = await self._pool.execute(query, root_id, list(scanned_ids))
        # res format: 'UPDATE 5'
        parts = res.split()
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    @staticmethod
    def _row_to_file_node(row: asyncpg.Record) -> FileNode:
        return FileNode(
            id=row["id"],
            root_id=row["root_id"],
            relative_path=row["relative_path"],
            physical_path=row["physical_path"],
            gdrive_id=row["gdrive_id"],
            file_name=row["file_name"],
            file_extension=row["file_extension"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            head_tail_xxh64=row["head_tail_xxh64"],
            content_sha256=row["content_sha256"],
            mtime=row["mtime"],
            ctime=row["ctime"],
            is_deleted=row["is_deleted"],
            sync_status=SyncStatus(row["sync_status"]),
            last_scanned_at=row["last_scanned_at"],
        )


class PostgresExtractionRepository:
    """PostgreSQL and pgvector implementation of ExtractionRepositoryPort."""

    def __init__(self, pool: DatabaseConnectionPool) -> None:
        self._pool = pool

    async def get_extraction(self, content_sha256: str) -> FileExtraction | None:
        query = "SELECT * FROM file_extractions WHERE content_sha256 = $1;"
        row = await self._pool.fetchrow(query, content_sha256)
        if row is None:
            return None
        meta = row["metadata_json"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        return FileExtraction(
            content_sha256=row["content_sha256"],
            extraction_strategy=row["extraction_strategy"],
            summary_text=row["summary_text"],
            metadata_json=meta or {},
            parser_version=row["parser_version"],
            extracted_at=row["extracted_at"],
        )

    async def save_extraction(self, extraction: FileExtraction) -> None:
        query = """
        INSERT INTO file_extractions (
            content_sha256, extraction_strategy, parser_version, summary_text, metadata_json, extracted_at
        ) VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (content_sha256) DO UPDATE SET
            summary_text = EXCLUDED.summary_text,
            metadata_json = EXCLUDED.metadata_json,
            extracted_at = NOW();
        """
        await self._pool.execute(
            query,
            extraction.content_sha256,
            extraction.extraction_strategy,
            extraction.parser_version,
            extraction.summary_text,
            json.dumps(extraction.metadata_json),
            extraction.extracted_at,
        )

    async def save_embedding(self, embedding: FileEmbedding) -> None:
        query = """
        INSERT INTO file_embeddings (id, content_sha256, model_name, embedding, created_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (content_sha256, model_name) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            created_at = NOW();
        """
        await self._pool.execute(
            query,
            embedding.id,
            embedding.content_sha256,
            embedding.model_name,
            embedding.embedding,
            embedding.created_at,
        )

    async def search_similar_vectors(
        self, query_vector: list[float], model_name: str, limit: int = 20
    ) -> list[tuple[str, float]]:
        query = """
        SELECT content_sha256, (embedding <=> $1) AS cosine_distance
        FROM file_embeddings
        WHERE model_name = $2
        ORDER BY embedding <=> $1
        LIMIT $3;
        """
        rows = await self._pool.fetch(query, query_vector, model_name, limit)
        return [(r["content_sha256"], float(r["cosine_distance"])) for r in rows]


class PostgresRuleRepository:
    """PostgreSQL implementation of RuleRepositoryPort."""

    def __init__(self, pool: DatabaseConnectionPool) -> None:
        self._pool = pool

    async def save_rule(self, rule: OrganizationRule) -> OrganizationRule:
        query = """
        INSERT INTO organization_rules (
            id, rule_name, description, source_root_id, source_pattern,
            condition_json, target_root_id, target_path_template, state,
            dry_run_last_count, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (id) DO UPDATE SET
            rule_name = EXCLUDED.rule_name,
            description = EXCLUDED.description,
            source_pattern = EXCLUDED.source_pattern,
            condition_json = EXCLUDED.condition_json,
            target_path_template = EXCLUDED.target_path_template,
            state = EXCLUDED.state,
            dry_run_last_count = EXCLUDED.dry_run_last_count,
            updated_at = NOW()
        RETURNING *;
        """
        row = await self._pool.fetchrow(
            query,
            rule.id,
            rule.rule_name,
            rule.description,
            rule.source_root_id,
            rule.source_pattern,
            json.dumps(rule.condition_json),
            rule.target_root_id,
            rule.target_path_template,
            rule.state.value,
            rule.dry_run_last_count,
            rule.created_at,
            rule.updated_at,
        )
        assert row is not None
        cond = row["condition_json"]
        if isinstance(cond, str):
            cond = json.loads(cond)
        return OrganizationRule(
            id=row["id"],
            rule_name=row["rule_name"],
            description=row["description"],
            source_root_id=row["source_root_id"],
            source_pattern=row["source_pattern"],
            condition_json=cond or {},
            target_root_id=row["target_root_id"],
            target_path_template=row["target_path_template"],
            state=RuleState(row["state"]),
            dry_run_last_count=row["dry_run_last_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_rule(self, rule_id: UUID) -> OrganizationRule | None:
        query = "SELECT * FROM organization_rules WHERE id = $1;"
        row = await self._pool.fetchrow(query, rule_id)
        if row is None:
            return None
        cond = row["condition_json"]
        if isinstance(cond, str):
            cond = json.loads(cond)
        return OrganizationRule(
            id=row["id"],
            rule_name=row["rule_name"],
            description=row["description"],
            source_root_id=row["source_root_id"],
            source_pattern=row["source_pattern"],
            condition_json=cond or {},
            target_root_id=row["target_root_id"],
            target_path_template=row["target_path_template"],
            state=RuleState(row["state"]),
            dry_run_last_count=row["dry_run_last_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def list_rules(self, state: RuleState | None = None) -> list[OrganizationRule]:
        if state is not None:
            query = "SELECT * FROM organization_rules WHERE state = $1 ORDER BY created_at;"
            rows = await self._pool.fetch(query, state.value)
        else:
            query = "SELECT * FROM organization_rules ORDER BY created_at;"
            rows = await self._pool.fetch(query)

        rules = []
        for r in rows:
            cond = r["condition_json"]
            if isinstance(cond, str):
                cond = json.loads(cond)
            rules.append(
                OrganizationRule(
                    id=r["id"],
                    rule_name=r["rule_name"],
                    description=r["description"],
                    source_root_id=r["source_root_id"],
                    source_pattern=r["source_pattern"],
                    condition_json=cond or {},
                    target_root_id=r["target_root_id"],
                    target_path_template=r["target_path_template"],
                    state=RuleState(r["state"]),
                    dry_run_last_count=r["dry_run_last_count"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
            )
        return rules

    async def update_rule_state(self, rule_id: UUID, new_state: RuleState) -> bool:
        query = "UPDATE organization_rules SET state = $1, updated_at = NOW() WHERE id = $2;"
        res = await self._pool.execute(query, new_state.value, rule_id)
        return "UPDATE 1" in res


class PostgresExecutionLedger:
    """PostgreSQL implementation of ExecutionLedgerPort."""

    def __init__(self, pool: DatabaseConnectionPool) -> None:
        self._pool = pool

    async def append_record(self, record: ExecutionRecord) -> None:
        query = """
        INSERT INTO execution_log (
            id, batch_id, rule_id, file_id, source_path, destination_path,
            source_sha256, operation_type, rollback_state, executed_at, reverted_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11);
        """
        await self._pool.execute(
            query,
            record.id,
            record.batch_id,
            record.rule_id,
            record.file_id,
            record.source_path,
            record.destination_path,
            record.source_sha256,
            record.operation_type.value,
            record.rollback_state.value,
            record.executed_at,
            record.reverted_at,
        )

    async def list_batch_records(self, batch_id: UUID) -> list[ExecutionRecord]:
        query = "SELECT * FROM execution_log WHERE batch_id = $1 ORDER BY executed_at DESC;"
        rows = await self._pool.fetch(query, batch_id)
        return [
            ExecutionRecord(
                id=r["id"],
                batch_id=r["batch_id"],
                rule_id=r["rule_id"],
                file_id=r["file_id"],
                source_path=r["source_path"],
                destination_path=r["destination_path"],
                source_sha256=r["source_sha256"],
                operation_type=OperationType(r["operation_type"]),
                rollback_state=RollbackState(r["rollback_state"]),
                executed_at=r["executed_at"],
                reverted_at=r["reverted_at"],
            )
            for r in rows
        ]

    async def update_record_state(self, record_id: UUID, new_state: RollbackState) -> None:
        query = "UPDATE execution_log SET rollback_state = $1, reverted_at = NOW() WHERE id = $2;"
        await self._pool.execute(query, new_state.value, record_id)
