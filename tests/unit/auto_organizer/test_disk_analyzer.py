"""Tests for FastDiskScanner and DiskAnalyzerUseCase."""

from pathlib import Path
import pytest

from hermes_auto_organizer.application.use_cases.disk_analyzer import DiskAnalyzerUseCase
from hermes_auto_organizer.domain.models import CleanupLevel
from hermes_auto_organizer.infrastructure.storage.fast_disk_scanner import FastDiskScanner


def test_fast_disk_scanner_and_analyzer_csv(tmp_path: Path):
    folder = tmp_path / "cache_dir"
    folder.mkdir()
    (folder / "large.bin").write_bytes(b"A" * 1024 * 100)
    (folder / "small.txt").write_bytes(b"B" * 50)
    sub = folder / "subfolder"
    sub.mkdir()
    (sub / "nested.dat").write_bytes(b"C" * 500)

    scanner = FastDiskScanner()
    use_case = DiskAnalyzerUseCase(scanner)

    entries = use_case.analyze_directory(str(folder))
    assert len(entries) >= 3
    # Top child should be large.bin
    assert entries[1].path.endswith("large.bin")
    assert entries[1].total_size == 1024 * 100

    csv_output = use_case.analyze_directory_csv(str(folder))
    assert "path,totalSize,type" in csv_output
    assert "large.bin" in csv_output


def test_evaluate_trash_candidates_filtering(tmp_path: Path):
    scanner = FastDiskScanner()
    use_case = DiskAnalyzerUseCase(scanner)

    raw_candidates = [
        {"path": "/etc", "size": 1000, "level": 0},  # Unsafe - must be rejected
        {"path": "/tmp/app_cache", "size": 5000, "level": 0, "reason": "Chrome cache"},
        {"path": "/tmp/app_cache/data", "size": 2000, "level": 0},  # Nested - must be pruned
        {"path": "/home/mb/Videos/large.mkv", "size": 20000000, "level": 1, "reason": "Podcast video"},
    ]

    candidates = use_case.evaluate_trash_candidates(raw_candidates)
    paths = [c.path for c in candidates]

    assert any("app_cache" in p for p in paths)
    assert not any(p == "/etc" for p in paths)
    assert not any("data" in p for p in paths)  # nested pruned
    assert any("large.mkv" in p for p in paths)
