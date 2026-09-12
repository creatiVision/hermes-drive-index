"""
Domain entities and immutable data structures for Hermes Auto-Organizer.
Follows Clean Architecture and Domain-Driven Design (DDD) principles:
pure data structures, no infrastructure, database, or network imports.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StorageRootType(str, Enum):
    LOCAL_DIR = "local_dir"
    GDRIVE_ROOT = "gdrive_root"
    NETWORK_SMB = "network_smb"


class WatchMode(str, Enum):
    INOTIFY = "inotify"
    POLL = "poll"
    MANUAL = "manual"


class SyncStatus(str, Enum):
    CLEAN = "clean"
    MODIFIED = "modified"
    CONFLICT = "conflict"
    MISSING = "missing"


class AnomalyType(str, Enum):
    DUMP_ZONE = "dump_zone"
    ORPHAN_FILE = "orphan_file"
    MISPLACED_CLUSTER = "misplaced_cluster"
    EXACT_DUPLICATE = "exact_duplicate"


class AnomalyStatus(str, Enum):
    OPEN = "open"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class RuleState(str, Enum):
    DRAFT = "DRAFT"
    STAGED = "STAGED"
    USER_APPROVED = "USER_APPROVED"
    DISABLED = "DISABLED"


class OperationType(str, Enum):
    LOCAL_MOVE = "LOCAL_MOVE"
    CROSS_FS_COPY_DELETE = "CROSS_FS_COPY_DELETE"
    GDRIVE_MOVE = "GDRIVE_MOVE"
    DIRECTORY_MOVE = "DIRECTORY_MOVE"
    TRASH_DELETE = "TRASH_DELETE"


class RollbackState(str, Enum):
    EXECUTED = "EXECUTED"
    REVERTED = "REVERTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class StorageRoot:
    """Represents a monitored storage root or namespace."""

    id: UUID = field(default_factory=uuid4)
    root_name: str = ""
    root_type: StorageRootType = StorageRootType.LOCAL_DIR
    uri_path: str = ""
    watch_mode: WatchMode = WatchMode.POLL
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class FileNode:
    """Represents a physical file at a given point in time (Now-State)."""

    id: UUID = field(default_factory=uuid4)
    root_id: UUID = field(default_factory=uuid4)
    relative_path: str = ""
    physical_path: str = ""
    file_name: str = ""
    size_bytes: int = 0
    mtime: datetime = field(default_factory=_utc_now)
    gdrive_id: str | None = None
    file_extension: str | None = None
    mime_type: str | None = None
    head_tail_xxh64: str | None = None
    content_sha256: str | None = None
    ctime: datetime | None = None
    is_deleted: bool = False
    sync_status: SyncStatus = SyncStatus.CLEAN
    last_scanned_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class FileExtraction:
    """Content summary and structured extraction keyed by content hash."""

    content_sha256: str
    extraction_strategy: str
    summary_text: str
    metadata_json: dict[str, Any] = field(default_factory=dict)
    parser_version: int = 1
    extracted_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class FileEmbedding:
    """Vector representation of an extracted file summary."""

    id: UUID = field(default_factory=uuid4)
    content_sha256: str = ""
    model_name: str = "text-embedding-3-small"
    embedding: list[float] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class StructuralAnomaly:
    """Flagged anomaly such as a dump zone, duplicate, or orphan file."""

    id: UUID = field(default_factory=uuid4)
    file_id: UUID = field(default_factory=uuid4)
    anomaly_type: AnomalyType = AnomalyType.DUMP_ZONE
    confidence: float = 1.0
    explanation: str = ""
    recommended_action: str | None = None
    status: AnomalyStatus = AnomalyStatus.OPEN
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class OrganizationRule:
    """Synthesized deterministic match-and-move rule."""

    id: UUID = field(default_factory=uuid4)
    rule_name: str = ""
    source_pattern: str = ""
    target_path_template: str = ""
    source_root_id: UUID | None = None
    target_root_id: UUID | None = None
    condition_json: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    state: RuleState = RuleState.DRAFT
    dry_run_last_count: int = 0
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class MoveIntent:
    """Proposed or validated move operation for dry-run and execution."""

    file_id: UUID
    source_path: str
    destination_path: str
    source_sha256: str
    operation_type: OperationType
    rule_id: UUID | None = None
    is_cross_device: bool = False
    requires_collision_rename: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    """Audit log entry for an executed operation supporting LIFO rollback."""

    id: UUID = field(default_factory=uuid4)
    batch_id: UUID = field(default_factory=uuid4)
    source_path: str = ""
    destination_path: str = ""
    source_sha256: str = ""
    operation_type: OperationType = OperationType.LOCAL_MOVE
    rollback_state: RollbackState = RollbackState.EXECUTED
    rule_id: UUID | None = None
    file_id: UUID | None = None
    executed_at: datetime = field(default_factory=_utc_now)
    reverted_at: datetime | None = None


class CleanupLevel(int, Enum):
    """Safety classification for disk cleaning candidates (inspired by ai-disk-cleaner)."""
    SAFE_CACHE = 0      # Level 0: Safe auto-regenerating caches, temp files, crash dumps, logs
    MIGRATION = 1       # Level 1: Migration candidates (heavy models, videos, old backups)
    RISKY_CONFIRM = 2   # Level 2: Requires explicit human review (app data, sync directories, DBs)


class MigrationStatus(str, Enum):
    """Status of a symlink directory migration."""
    ACTIVE = "ACTIVE"
    REVERTED = "REVERTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TrashCandidate:
    """A file or directory identified as candidate for removal or cleanup."""
    path: str
    size_bytes: int
    level: CleanupLevel = CleanupLevel.SAFE_CACHE
    reason: str = ""
    name: str = ""
    source_device: str = "laptop"
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class DiskUsageEntry:
    """Directory tree usage node for progressive analysis (path, size, type)."""
    path: str
    total_size: int
    type_id: int = 0  # 0 for directory, 1 for regular file
    file_count: int = 1


@dataclass(frozen=True, slots=True)
class MigrationRecord:
    """Tracks a directory migrated to another disk with a symlink left behind."""
    id: UUID = field(default_factory=uuid4)
    source_path: str = ""
    destination_path: str = ""
    size_bytes: int = 0
    symlink_created: bool = True
    status: MigrationStatus = MigrationStatus.ACTIVE
    created_at: datetime = field(default_factory=_utc_now)
    reverted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class LanDeviceNode:
    """Represents an accessible machine in the LAN mesh."""
    device_id: str
    name: str
    addresses: tuple[str, ...] = ()
    synced_folders: tuple[str, ...] = ()
    is_online: bool = False


@dataclass(frozen=True, slots=True)
class GDriveSelectiveMapping:
    """Configured selective sync mapping between a local directory and a Drive path."""
    name: str
    local_path: str
    drive_folder_path: str
    direction: str = "bidirectional"
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    status: str = "in_sync"

