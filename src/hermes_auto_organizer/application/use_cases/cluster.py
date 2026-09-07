"""
Clustering and anomaly detection use cases.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence
from uuid import uuid4

from hermes_auto_organizer.domain.models import (
    AnomalyStatus,
    AnomalyType,
    FileNode,
    StructuralAnomaly,
)


class AnomalyDetector:
    """Identifies dump zone clutter, exact duplicates, and misplaced files."""

    DUMP_ZONE_NAMES = {"downloads", "desktop", "schreibtisch", "temp", "tmp"}

    @classmethod
    def detect_anomalies(cls, nodes: Sequence[FileNode]) -> list[StructuralAnomaly]:
        anomalies: list[StructuralAnomaly] = []

        # 1. Exact Duplicates by SHA-256
        hash_map: dict[str, list[FileNode]] = defaultdict(list)
        for node in nodes:
            if node.content_sha256:
                hash_map[node.content_sha256].append(node)

        for sha, duplicates in hash_map.items():
            if len(duplicates) > 1:
                for dup in duplicates[1:]:
                    anomalies.append(
                        StructuralAnomaly(
                            id=uuid4(),
                            file_id=dup.id,
                            anomaly_type=AnomalyType.EXACT_DUPLICATE,
                            confidence=1.0,
                            explanation=f"Exact duplicate of '{duplicates[0].physical_path}' (SHA-256: {sha[:8]}).",
                            recommended_action="Archive or trash duplicate file.",
                            status=AnomalyStatus.OPEN,
                        )
                    )

        # 2. Dump Zone Files
        for node in nodes:
            parts = [p.lower() for p in node.relative_path.split("/")]
            if any(part in cls.DUMP_ZONE_NAMES for part in parts):
                anomalies.append(
                    StructuralAnomaly(
                        id=uuid4(),
                        file_id=node.id,
                        anomaly_type=AnomalyType.DUMP_ZONE,
                        confidence=0.9,
                        explanation=f"File '{node.file_name}' resides in unorganized dump directory '{node.relative_path}'.",
                        recommended_action="Classify into Ideal Tree taxonomy.",
                        status=AnomalyStatus.OPEN,
                    )
                )

        return anomalies
