"""
Unit tests for domain policies (boundary, collision, rule states).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from pathlib import Path
import pytest

from hermes_auto_organizer.domain.models import RuleState
from hermes_auto_organizer.domain.policies import (
    BoundaryPolicy,
    CollisionPolicy,
    PolicyViolationError,
    RuleStatePolicy,
)


def test_boundary_policy_valid_containment(tmp_path: Path):
    subfolder = tmp_path / "documents" / "nested"
    subfolder.mkdir(parents=True)
    target_file = subfolder / "test.txt"

    resolved = BoundaryPolicy.assert_contained(target_file, tmp_path)
    assert resolved == target_file.resolve()


def test_boundary_policy_detects_traversal(tmp_path: Path):
    root = tmp_path / "sandbox"
    root.mkdir()
    outside_file = tmp_path / "outside.txt"

    with pytest.raises(PolicyViolationError, match="Path traversal detected"):
        BoundaryPolicy.assert_contained(outside_file, root)


def test_boundary_policy_cannot_be_root_itself(tmp_path: Path):
    with pytest.raises(PolicyViolationError, match="Target path cannot be the root itself"):
        BoundaryPolicy.assert_contained(tmp_path, tmp_path)


def test_collision_policy_path_generation(tmp_path: Path):
    colliding_file = tmp_path / "sample.pdf"
    content_hash = "abcdef1234567890"

    safe_path = CollisionPolicy.resolve_collision_path(colliding_file, content_hash)
    assert safe_path.parent == tmp_path
    assert safe_path.suffix == ".pdf"
    assert "_conflict_" in safe_path.stem
    assert "abcdef12" in safe_path.stem


def test_rule_state_valid_transitions():
    RuleStatePolicy.assert_valid_transition(RuleState.DRAFT, RuleState.STAGED)
    RuleStatePolicy.assert_valid_transition(RuleState.STAGED, RuleState.USER_APPROVED)
    RuleStatePolicy.assert_valid_transition(RuleState.USER_APPROVED, RuleState.DISABLED)


def test_rule_state_invalid_transitions():
    with pytest.raises(PolicyViolationError, match="Invalid rule transition"):
        RuleStatePolicy.assert_valid_transition(RuleState.DRAFT, RuleState.USER_APPROVED)
