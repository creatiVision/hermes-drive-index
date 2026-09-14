"""
Port interface for recursive subtree profiling and structural disruption analysis.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Protocol

from hermes_auto_organizer.domain.profiler_models import (
    DisruptionItem,
    FolderProfile,
    NaturalLanguageRule,
    OutlierItem,
    TreeDiffNode,
)


class SubtreeProfilerPort(Protocol):
    """Contract for recursive bottom-up directory profiling and disruption analysis."""

    def profile_directory(
        self,
        path: Path | str,
        max_depth: int = 8,
        include_hidden: bool = False,
    ) -> FolderProfile:
        """Recursively scan path and return a bottom-up aggregated FolderProfile tree."""
        ...

    def detect_disruptions(self, profile: FolderProfile) -> List[DisruptionItem]:
        """Analyze folder profile for structural disruptions, dump zones, and anti-patterns."""
        ...

    def detect_outliers(self, profile: FolderProfile) -> List[OutlierItem]:
        """Identify individual file/folder outliers and generate concrete solution proposals."""
        ...

    def synthesize_rules(self, profile: FolderProfile) -> List[NaturalLanguageRule]:
        """Synthesize human-readable German meta-rules for bulk data clusters."""
        ...

    def compute_tree_diff(
        self,
        profile: FolderProfile,
        confirmed_rules: List[NaturalLanguageRule],
        resolved_outliers: List[OutlierItem],
    ) -> List[TreeDiffNode]:
        """Project the ideal state (S_ideal) against S_now and return the tree-diff manifest."""
        ...
