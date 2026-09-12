"""
Domain models for Subtree Profiler, Disruption Detection, NL Rules, and Tree-Diff.

Follows Clean Architecture & DDD principles:
Pure immutable domain models with zero I/O or external library dependencies.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DisruptionType(str, Enum):
    DUMP_ZONE = "DUMP_ZONE"
    MIXED_LIFECYCLE = "MIXED_LIFECYCLE"
    TYPE_OUTLIER = "TYPE_OUTLIER"
    MISPLACED_FOLDER = "MISPLACED_FOLDER"
    DEEP_NESTING = "DEEP_NESTING"
    ROOT_POLLUTION = "ROOT_POLLUTION"
    ORPHAN_MEDIA = "ORPHAN_MEDIA"
    CLEANABLE_TEMP = "CLEANABLE_TEMP"


class DisruptionSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class LifecycleDistribution:
    """Age breakdown of files in a subtree."""
    active_count: int = 0      # < 30 days
    dormant_count: int = 0     # 30-365 days
    cold_count: int = 0        # > 365 days
    total_count: int = 0

    @property
    def active_ratio(self) -> float:
        return self.active_count / max(1, self.total_count)

    @property
    def cold_ratio(self) -> float:
        return self.cold_count / max(1, self.total_count)

    @property
    def dormant_ratio(self) -> float:
        return self.dormant_count / max(1, self.total_count)


@dataclass(frozen=True, slots=True)
class DisruptionItem:
    """Structural disruption or anti-pattern detected in a folder."""
    id: str = field(default_factory=lambda: str(uuid4()))
    disruption_type: DisruptionType = DisruptionType.DUMP_ZONE
    severity: DisruptionSeverity = DisruptionSeverity.WARNING
    description: str = ""
    detected_path: str = ""
    metric_value: float = 0.0


@dataclass(frozen=True, slots=True)
class SolutionProposal:
    """Concrete solution proposal for a single outlier or disruption."""
    target_path: str
    confidence: float
    reasoning_de: str
    action_type: str = "MOVE"  # "MOVE", "ARCHIVE", "CLEAN"


@dataclass(frozen=True, slots=True)
class OutlierItem:
    """Single outlier (e.g. project folder inside Downloads) in the Human-in-the-Middle queue."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_path: str = ""
    disruption_type: DisruptionType = DisruptionType.TYPE_OUTLIER
    reason_de: str = ""
    proposal: SolutionProposal = field(default_factory=lambda: SolutionProposal("", 0.0, ""))
    status: str = "pending"  # "pending", "approved", "rejected", "customized"
    custom_target_path: Optional[str] = None


@dataclass(frozen=True, slots=True)
class NaturalLanguageRule:
    """Human-readable synthesized meta-rule in German for the 90% bulk cases."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title_de: str = ""
    description_de: str = ""
    condition_json: Dict[str, Any] = field(default_factory=dict)
    target_path_template: str = ""
    affected_files_count: int = 0
    affected_bytes: int = 0
    confidence: float = 0.85
    status: str = "proposed"  # "proposed", "approved", "rejected"


@dataclass
class FolderProfile:
    """Recursive bottom-up profile of a directory node."""
    path: str
    name: str
    depth: int = 0
    direct_files_count: int = 0
    direct_bytes: int = 0
    total_files_count: int = 0
    total_bytes: int = 0
    direct_subdirs_count: int = 0
    total_subdirs_count: int = 0
    mime_entropy: float = 0.0  # 0.0 (homogeneous) to 1.0 (chaotic)
    dominant_extension: str = ""
    extension_counts: Dict[str, int] = field(default_factory=dict)
    lifecycle: LifecycleDistribution = field(default_factory=LifecycleDistribution)
    root_pollution_ratio: float = 0.0  # direct_files / max(1, total_files)
    disruptions: List[DisruptionItem] = field(default_factory=list)
    subfolders: List[FolderProfile] = field(default_factory=list)

    @staticmethod
    def calculate_mime_entropy(extension_counts: Dict[str, int]) -> float:
        """
        Computes normalized Shannon entropy (0.0 to 1.0).
        0.0 = single file type (completely homogeneous).
        1.0 = highly chaotic mixture of many different extensions.
        """
        total = sum(extension_counts.values())
        if total <= 1 or len(extension_counts) <= 1:
            return 0.0

        n_categories = len(extension_counts)
        max_entropy = math.log2(n_categories)
        if max_entropy <= 0:
            return 0.0

        entropy = 0.0
        for count in extension_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        return min(1.0, max(0.0, entropy / max_entropy))


@dataclass(frozen=True, slots=True)
class TreeDiffNode:
    """Represents a node in the 'Von -> Nach' (S_now -> S_ideal) comparison."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    source_path: str = ""
    target_path: Optional[str] = None
    action: str = "RETAIN"  # "RETAIN", "MOVE", "CLEAN_TEMP", "ARCHIVE"
    rule_id: Optional[str] = None
    reason_de: str = ""
    size_bytes: int = 0
    is_directory: bool = False
    is_outlier: bool = False
    status: str = "preview"  # "preview", "staged", "executed"
