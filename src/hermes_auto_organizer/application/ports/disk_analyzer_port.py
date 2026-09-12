"""
Disk Analyzer and Migration Port Protocols for Hermes Auto-Organizer.
Follows Hexagonal Architecture: defines abstract interfaces for disk scanning,
symlink migrations, and LAN mesh topology discovery.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from hermes_auto_organizer.domain.models import (
    DiskUsageEntry,
    MigrationRecord,
    TrashCandidate,
)


class DiskScannerPort(Protocol):
    """Abstract port for progressive disk usage scanning and entry analysis."""

    def analyze_directory(self, target_path: str, max_entries: int = 200) -> list[DiskUsageEntry]:
        """Inspect a directory and return usage entries for itself and its top children."""
        ...

    def get_mount_usages(self) -> list[dict[str, Any]]:
        """Return total, used, free space and status for all active host mount points."""
        ...


class MigrationPort(Protocol):
    """Abstract port for moving heavy directories across drives with symlinks."""

    def copy_source(self, source_path: str, destination_dir: str, name: str) -> str:
        """Copy source directory to destination_dir/name safely."""
        ...

    def delete_source(self, source_path: str, destination_path: str) -> None:
        """Delete source directory only after destination copy is verified."""
        ...

    def create_symlink(self, target_dest: str, link_source: str) -> None:
        """Create symbolic link pointing from link_source to target_dest."""
        ...

    def rollback_migration(self, record: MigrationRecord) -> bool:
        """Revert migration: restore files from destination to source, removing symlink."""
        ...


class LanMeshPort(Protocol):
    """Abstract port for querying multi-device LAN topology and Syncthing states."""

    def get_devices(self) -> list[dict[str, Any]]:
        """Return connected devices (laptop, debian1, xiaomi-mobile) and status."""
        ...

    def get_syncthing_folders(self) -> list[dict[str, Any]]:
        """Return configured Syncthing folders, sync states, and peer mappings."""
        ...

    def get_root_triage(self) -> list[dict[str, Any]]:
        """Identify loose, misplaced files sitting in root of partitions."""
        ...
