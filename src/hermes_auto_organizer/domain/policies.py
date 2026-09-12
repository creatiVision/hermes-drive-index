"""
Domain business policies for Hermes Auto-Organizer.
Contains pure decision logic: collision avoidance, boundary sandboxing,
and state transition validations.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hermes_auto_organizer.domain.models import RuleState


class PolicyViolationError(ValueError):
    """Raised when an operation violates domain safety invariants."""


class BoundaryPolicy:
    """Enforces strict path containment within allowed storage roots."""

    @staticmethod
    def assert_contained(target_path: Path, root_path: Path) -> Path:
        """
        Verify that target_path resolves strictly within root_path.
        Prevents path traversal ('..') or unauthorized filesystem escape.
        """
        resolved_root = root_path.resolve()
        resolved_target = target_path.resolve()

        if resolved_target == resolved_root:
            raise PolicyViolationError(f"Target path cannot be the root itself: {target_path}")

        try:
            resolved_target.relative_to(resolved_root)
        except ValueError:
            raise PolicyViolationError(
                f"Path traversal detected: {target_path} is outside allowed root {root_path}"
            )
        return resolved_target


class CollisionPolicy:
    """Calculates non-destructive destination paths when collisions occur."""

    @staticmethod
    def resolve_collision_path(target_path: Path, content_hash: str | None = None) -> Path:
        """
        Generate a collision-safe path using timestamp and hash suffix.
        Guarantees zero silent overwrites.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        hash_suffix = f"_{content_hash[:8]}" if content_hash else ""
        parent = target_path.parent
        stem = target_path.stem
        suffix = target_path.suffix

        new_name = f"{stem}_conflict_{timestamp}{hash_suffix}{suffix}"
        return parent / new_name


class RuleStatePolicy:
    """Enforces valid lifecycle transitions for organization rules."""

    _ALLOWED_TRANSITIONS: dict[RuleState, set[RuleState]] = {
        RuleState.DRAFT: {RuleState.STAGED, RuleState.DISABLED},
        RuleState.STAGED: {RuleState.USER_APPROVED, RuleState.DRAFT, RuleState.DISABLED},
        RuleState.USER_APPROVED: {RuleState.STAGED, RuleState.DISABLED},
        RuleState.DISABLED: {RuleState.DRAFT, RuleState.STAGED},
    }

    @classmethod
    def assert_valid_transition(cls, current: RuleState, target: RuleState) -> None:
        """Verify that state transition is permitted by domain rules."""
        if current == target:
            return
        allowed = cls._ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise PolicyViolationError(
                f"Invalid rule transition from '{current.value}' to '{target.value}'. Allowed: {[s.value for s in allowed]}"
            )
