"""
Disk Analyzer Use Case.
Orchestrates progressive disk drill-down inspection, trash candidate collection,
and boundary deduplication (inspired by ai-disk-cleaner).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any, List, Optional

from hermes_auto_organizer.application.ports.disk_analyzer_port import DiskScannerPort
from hermes_auto_organizer.domain.models import CleanupLevel, DiskUsageEntry, TrashCandidate
from hermes_auto_organizer.domain.policies import DiskCleaningPolicy, PolicyViolationError

logger = logging.getLogger("hermes_auto_organizer.use_cases.disk_analyzer")


class DiskAnalyzerUseCase:
    """Use case for progressive directory analysis and trash candidate evaluation."""

    def __init__(self, scanner: DiskScannerPort) -> None:
        self._scanner = scanner

    def analyze_directory(self, path: str, max_entries: int = 200) -> list[DiskUsageEntry]:
        """Drill down into path and retrieve top usage entries."""
        clean_path = DiskCleaningPolicy.normalize_path(path)
        if not clean_path or not Path(clean_path).exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        return self._scanner.analyze_directory(clean_path, max_entries=max_entries)

    def analyze_directory_csv(self, path: str, max_entries: int = 200) -> str:
        """Format directory usage entries as CSV for LLM token efficiency."""
        entries = self.analyze_directory(path, max_entries=max_entries)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["path", "totalSize", "type"])
        for entry in entries:
            writer.writerow([entry.path, entry.total_size, entry.type_id])
        return output.getvalue()

    def evaluate_trash_candidates(self, candidates_raw: list[dict[str, Any]]) -> list[TrashCandidate]:
        """
        Validate, classify, and deduplicate trash candidates.
        Enforces system safety and non-nested deletion boundaries.
        """
        validated: list[TrashCandidate] = []
        for raw in candidates_raw:
            path_str = raw.get("path", "").strip()
            if not path_str:
                continue

            # Ensure system safety policy
            try:
                DiskCleaningPolicy.assert_cleanup_safe(path_str)
            except PolicyViolationError as e:
                logger.warning("Rejected unsafe candidate path '%s': %s", path_str, e)
                continue

            level_val = raw.get("level", 0)
            try:
                level = CleanupLevel(level_val)
            except (ValueError, TypeError):
                level = CleanupLevel.SAFE_CACHE

            cand = TrashCandidate(
                path=DiskCleaningPolicy.normalize_path(path_str),
                size_bytes=int(raw.get("size_bytes", raw.get("size", 0))),
                level=level,
                reason=raw.get("reason", ""),
                name=raw.get("name", Path(path_str).name),
                source_device=raw.get("source_device", "laptop"),
            )
            validated.append(cand)

        # Eliminate nested candidate paths (keep exact boundaries)
        deduped = DiskCleaningPolicy.remove_nested_trash_candidates(validated)
        return deduped
