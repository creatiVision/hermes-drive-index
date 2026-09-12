"""Tests for DiskCleaningPolicy boundary deduplication and safety rules."""

import pytest
from hermes_auto_organizer.domain.models import CleanupLevel, TrashCandidate
from hermes_auto_organizer.domain.policies import DiskCleaningPolicy, PolicyViolationError


def test_normalize_path():
    assert DiskCleaningPolicy.normalize_path("  /tmp/foo/../bar  ") != ""
    assert DiskCleaningPolicy.normalize_path("") == ""


def test_is_path_inside():
    assert DiskCleaningPolicy.is_path_inside("/home/mb/Downloads/file.zip", "/home/mb/Downloads") is True
    assert DiskCleaningPolicy.is_path_inside("/home/mb/Downloads", "/home/mb/Downloads") is False
    assert DiskCleaningPolicy.is_path_inside("/var/log", "/home/mb") is False


def test_same_path():
    assert DiskCleaningPolicy.same_path("/tmp/test/./foo", "/tmp/test/foo") is True
    assert DiskCleaningPolicy.same_path("/tmp/foo", "/tmp/bar") is False


def test_critical_system_paths_rejection():
    with pytest.raises(PolicyViolationError):
        DiskCleaningPolicy.assert_cleanup_safe("/etc")

    with pytest.raises(PolicyViolationError):
        DiskCleaningPolicy.assert_cleanup_safe("/usr")

    with pytest.raises(PolicyViolationError):
        DiskCleaningPolicy.assert_cleanup_safe("/media/work-data")

    # Safe subpath should not raise
    DiskCleaningPolicy.assert_cleanup_safe("/media/work-data/911_IT-wiki/test.mp4")


def test_remove_nested_trash_candidates():
    candidates = [
        TrashCandidate(path="/home/mb/.cache", size_bytes=5000, level=CleanupLevel.SAFE_CACHE),
        TrashCandidate(path="/home/mb/.cache/pip", size_bytes=2000, level=CleanupLevel.SAFE_CACHE),
        TrashCandidate(path="/home/mb/Downloads/test.iso", size_bytes=1000, level=CleanupLevel.MIGRATION),
        TrashCandidate(path="/home/mb/.cache", size_bytes=5000, level=CleanupLevel.SAFE_CACHE),  # Duplicate
    ]

    deduped = DiskCleaningPolicy.remove_nested_trash_candidates(candidates)
    assert len(deduped) == 2
    paths = [c.path for c in deduped]
    assert "/home/mb/.cache" in paths
    assert "/home/mb/Downloads/test.iso" in paths
    assert "/home/mb/.cache/pip" not in paths
