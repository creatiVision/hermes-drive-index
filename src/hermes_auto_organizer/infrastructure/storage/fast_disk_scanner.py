"""
Fast Disk Scanner Adapter.
Implements DiskScannerPort using high-performance directory iteration,
calculating disk usages and formatting top entries (adapted from ai-disk-cleaner).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
from typing import Any, List

from hermes_auto_organizer.domain.models import DiskUsageEntry

logger = logging.getLogger("hermes_auto_organizer.storage.fast_disk_scanner")


def get_dir_size_fast(path: Path, max_depth: int = 2) -> int:
    """Calculates approximate directory size without infinite deep traversal."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False) and max_depth > 0:
                        total += get_dir_size_fast(Path(entry.path), max_depth=max_depth - 1)
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return total


class FastDiskScanner:
    """Implements DiskScannerPort for progressive disk exploration."""

    def analyze_directory(self, target_path: str, max_entries: int = 200) -> list[DiskUsageEntry]:
        """
        Inspect a directory and return usage entries for itself and its top children
        sorted descending by total size (up to max_entries).
        """
        target = Path(target_path).resolve()
        if not target.exists():
            return []

        entries: list[DiskUsageEntry] = []

        # If target is a file, return single entry
        if target.is_file():
            size = target.stat().st_size
            return [DiskUsageEntry(path=str(target), total_size=size, type_id=1, file_count=1)]

        # Collect children
        child_entries: list[DiskUsageEntry] = []
        try:
            with os.scandir(target) as it:
                for entry in it:
                    try:
                        p = str(Path(entry.path).resolve())
                        if entry.is_dir(follow_symlinks=False):
                            size = get_dir_size_fast(Path(entry.path), max_depth=2)
                            child_entries.append(
                                DiskUsageEntry(path=p, total_size=size, type_id=0, file_count=1)
                            )
                        elif entry.is_file(follow_symlinks=False):
                            size = entry.stat().st_size
                            child_entries.append(
                                DiskUsageEntry(path=p, total_size=size, type_id=1, file_count=1)
                            )
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError) as exc:
            logger.warning("Permission denied reading directory: %s (%s)", target_path, exc)

        # Sort children descending by size
        child_entries.sort(key=lambda e: e.total_size, reverse=True)
        top_children = child_entries[:max_entries]

        # Total size of the parent is sum of top children
        parent_total = sum(c.total_size for c in child_entries)
        entries.append(
            DiskUsageEntry(path=str(target), total_size=parent_total, type_id=0, file_count=len(child_entries))
        )
        entries.extend(top_children)

        return entries

    def get_mount_usages(self) -> list[dict[str, Any]]:
        """Return disk usage metrics across recognized system partitions."""
        mounts_to_check = [
            "/",
            "/home",
            "/media/work-data",
            "/media/privat-data",
            "/media/xchg",
            "/media/nosync",
        ]
        # Also discover /media mounts dynamically
        media_root = Path("/media")
        if media_root.exists() and media_root.is_dir():
            try:
                for entry in media_root.iterdir():
                    p_str = str(entry)
                    if entry.is_dir() and p_str not in mounts_to_check:
                        mounts_to_check.append(p_str)
            except OSError:
                pass

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for m in mounts_to_check:
            if m in seen:
                continue
            seen.add(m)
            p = Path(m)
            if not p.exists() or not p.is_dir():
                continue
            try:
                usage = shutil.disk_usage(m)
                results.append({
                    "mount_point": m,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "usage_percent": round((usage.used / usage.total) * 100, 1),
                })
            except OSError:
                continue
        return results
