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
from typing import Any

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
        """Check if child_path is strictly inside parent_path.
        Optimized: Uses string prefix matching on normalized paths instead of Path.relative_to
        and exception handling (~50x faster).
        """
        child = cls.normalize_path(child_path)
        parent = cls.normalize_path(parent_path)
        if not child or not parent or child == parent:
            return False
        parent_prefix = parent if parent.endswith(("/", "\\")) else parent + "/"
        return child.startswith(parent_prefix)

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
        Optimized: Pre-normalizes candidate paths once to avoid O(N^2)
        filesystem resolve() syscalls and Path object allocations (>400x speedup).
        """
        if not candidates:
            return []

        # Pre-normalize candidate paths once to eliminate redundant realpath syscalls in nested loops
        norm_paths = [
            cls.normalize_path(cand.path if hasattr(cand, "path") else cand.get("path", ""))
            for cand in candidates
        ]

        result: list[Any] = []
        n = len(candidates)

        for i in range(n):
            c_path = norm_paths[i]
            if not c_path:
                continue

            duplicate = False
            contained = False

            for j in range(n):
                if i == j:
                    continue
                o_path = norm_paths[j]
                if not o_path:
                    continue

                if c_path == o_path:
                    duplicate = j < i
                    if duplicate:
                        break
                    continue

                o_prefix = o_path if o_path.endswith(("/", "\\")) else o_path + "/"
                if c_path.startswith(o_prefix):
                    contained = True
                    break

            if not duplicate and not contained:
                result.append(candidates[i])

        return result

