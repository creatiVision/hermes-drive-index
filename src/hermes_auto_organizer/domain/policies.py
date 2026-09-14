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


class DiskCleaningPolicy:
    """
    Enforces precise deletion boundaries and prevents destructive actions
    (adapted from ai-disk-cleaner).
    """

    CRITICAL_SYSTEM_PATHS: set[str] = {
        "/", "/bin", "/boot", "/dev", "/etc", "/lib", "/lib64",
        "/proc", "/root", "/sbin", "/sys", "/usr", "/var"
    }

    @staticmethod
    def normalize_path(path_str: str) -> str:
        """Normalize path for exact comparisons."""
        clean = path_str.strip()
        if not clean:
            return ""
        return str(Path(clean).resolve())

    @classmethod
    def is_path_inside(cls, child_path: str, parent_path: str) -> bool:
        """Check if child_path is strictly inside parent_path."""
        child = cls.normalize_path(child_path)
        parent = cls.normalize_path(parent_path)
        if not child or not parent or child == parent:
            return False
        try:
            rel = Path(child).relative_to(Path(parent))
            return len(rel.parts) > 0
        except ValueError:
            return False

    @classmethod
    def same_path(cls, path_a: str, path_b: str) -> bool:
        """Check if two paths resolve to the exact same location."""
        a = cls.normalize_path(path_a)
        b = cls.normalize_path(path_b)
        return a != "" and a == b

    @classmethod
    def assert_cleanup_safe(cls, target_path: str) -> None:
        """
        Verify that path is not a critical OS root or direct system directory.
        Raises PolicyViolationError if unsafe.
        """
        normalized = cls.normalize_path(target_path)
        if normalized in cls.CRITICAL_SYSTEM_PATHS:
            raise PolicyViolationError(
                f"Critical system directory cannot be marked for cleanup: {target_path}"
            )
        # Avoid cleaning top-level mount roots directly
        if normalized in {"/home", "/media", "/media/work-data", "/media/privat-data", "/media/xchg", "/media/nosync"}:
            raise PolicyViolationError(
                f"Mount root cannot be deleted as a whole; specify a target subfolder: {target_path}"
            )

    @classmethod
    def remove_nested_trash_candidates(cls, candidates: list[Any]) -> list[Any]:
        """
        Deduplicate candidates and eliminate nested boundaries.
        Prevents double-deletion and overlapping operations.
        """
        result: list[Any] = []
        for i, cand in enumerate(candidates):
            c_path = cand.path if hasattr(cand, "path") else cand.get("path", "")
            duplicate = False
            contained = False

            for j, other in enumerate(candidates):
                if i == j:
                    continue
                o_path = other.path if hasattr(other, "path") else other.get("path", "")

                if cls.same_path(c_path, o_path):
                    duplicate = j < i
                    continue

                if cls.is_path_inside(c_path, o_path):
                    contained = True
                    break

            if not duplicate and not contained:
                result.append(cand)
        return result

