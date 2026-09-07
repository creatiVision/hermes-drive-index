"""
Dry-run verification and target path resolution engine.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Sequence

from hermes_auto_organizer.domain.models import (
    FileNode,
    MoveIntent,
    OperationType,
    OrganizationRule,
    StorageRoot,
)
from hermes_auto_organizer.domain.policies import BoundaryPolicy, CollisionPolicy
from hermes_auto_organizer.domain.rule_engine import (
    evaluate_modular_rule,
    resolve_destination_path,
)


class DryRunEngine:
    """Simulates rule execution and verifies safety constraints without altering disk."""

    @classmethod
    def simulate_rule(
        cls,
        rule: OrganizationRule,
        nodes: Sequence[FileNode],
        target_root: StorageRoot,
    ) -> list[MoveIntent]:
        intents: list[MoveIntent] = []
        target_root_path = Path(target_root.uri_path)

        for node in nodes:
            # 1. Evaluate modular rule conditions (folder, timeframe, keyword, extension, size)
            if not evaluate_modular_rule(
                rule.condition_json,
                node,
                source_pattern=rule.source_pattern,
            ):
                continue

            # 2. Resolve destination path template
            try:
                dest_rel = resolve_destination_path(rule.target_path_template, node)
            except Exception:
                dest_rel = rule.target_path_template.format(
                    file_name=node.file_name,
                    extension=node.file_extension or "",
                    stem=Path(node.file_name).stem,
                    year=node.mtime.strftime("%Y"),
                    month=node.mtime.strftime("%m"),
                )
            candidate_dest = target_root_path / dest_rel

            # 4. Boundary enforcement
            validated_dest = BoundaryPolicy.assert_contained(candidate_dest, target_root_path)

            # 5. Collision detection
            requires_collision = validated_dest.exists()
            if requires_collision:
                validated_dest = CollisionPolicy.resolve_collision_path(
                    validated_dest, node.content_sha256
                )

            # 6. Cross-device detection
            source_path = Path(node.physical_path)
            is_cross_device = False
            if source_path.exists() and target_root_path.exists():
                try:
                    is_cross_device = source_path.stat().st_dev != target_root_path.stat().st_dev
                except OSError:
                    is_cross_device = False

            op_type = (
                OperationType.CROSS_FS_COPY_DELETE
                if is_cross_device
                else OperationType.LOCAL_MOVE
            )

            intents.append(
                MoveIntent(
                    file_id=node.id,
                    source_path=node.physical_path,
                    destination_path=str(validated_dest),
                    source_sha256=node.content_sha256 or "",
                    operation_type=op_type,
                    rule_id=rule.id,
                    is_cross_device=is_cross_device,
                    requires_collision_rename=requires_collision,
                )
            )

        return intents
