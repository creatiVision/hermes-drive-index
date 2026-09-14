"""
Unit and benchmark tests verifying PR #15 LocalFilesystemScanner optimizations.

Tests:
1. S_ISREG skips non-regular files (e.g. FIFOs)
2. base_path resolution and relative path accuracy across subdirectories
3. mime_type guessing directly from filename
4. High file volume scanning benchmark (1,000 files)
"""

import asyncio
import os
import stat as stat_module
import time
from pathlib import Path
import pytest

from hermes_auto_organizer.domain.models import StorageRoot, StorageRootType, WatchMode
from hermes_auto_organizer.infrastructure.storage.local_scanner import LocalFilesystemScanner


def test_scanner_pr15_skips_non_regular_files(tmp_path: Path):
    """Verify that S_ISREG filters out non-regular files (e.g. named pipes/FIFOs)."""
    async def _run():
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        regular_file = data_dir / "regular.txt"
        regular_file.write_text("regular file content", encoding="utf-8")

        fifo_path = data_dir / "test_fifo"
        try:
            os.mkfifo(str(fifo_path))
            has_fifo = True
        except (AttributeError, OSError):
            has_fifo = False

        root = StorageRoot(
            root_name="test_root",
            root_type=StorageRootType.LOCAL_DIR,
            uri_path=str(tmp_path),
            watch_mode=WatchMode.POLL,
        )

        scanner = LocalFilesystemScanner()
        nodes = [node async for node in scanner.scan_root(root, compute_sha256=False)]
        return nodes, has_fifo

    nodes, has_fifo = asyncio.run(_run())
    file_names = {n.file_name for n in nodes}
    assert "regular.txt" in file_names
    if has_fifo:
        assert "test_fifo" not in file_names


def test_scanner_pr15_deep_structure_and_mimetypes(tmp_path: Path):
    """Verify scanning nested subdirectories, correct relative paths, and mime types."""
    async def _run():
        sub_dir = tmp_path / "folder_a" / "folder_b"
        sub_dir.mkdir(parents=True)
        pdf_file = sub_dir / "report.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 report dummy data")
        json_file = sub_dir / "meta.json"
        json_file.write_text('{"key": "value"}', encoding="utf-8")

        root = StorageRoot(
            root_name="nested_root",
            root_type=StorageRootType.LOCAL_DIR,
            uri_path=str(tmp_path),
            watch_mode=WatchMode.POLL,
        )

        scanner = LocalFilesystemScanner()
        return [node async for node in scanner.scan_root(root, compute_sha256=True)]

    nodes = asyncio.run(_run())
    assert len(nodes) == 2
    by_name = {n.file_name: n for n in nodes}

    assert "report.pdf" in by_name
    pdf_node = by_name["report.pdf"]
    assert pdf_node.relative_path == "folder_a/folder_b/report.pdf"
    assert pdf_node.mime_type == "application/pdf"
    assert pdf_node.content_sha256 is not None
    assert pdf_node.physical_path.endswith("folder_a/folder_b/report.pdf")

    assert "meta.json" in by_name
    json_node = by_name["meta.json"]
    assert json_node.relative_path == "folder_a/folder_b/meta.json"
    assert json_node.mime_type == "application/json"


def test_scanner_pr15_benchmark_1000_files(tmp_path: Path):
    """Benchmark scanning 1,000 files across multiple subdirectories."""
    async def _run():
        num_dirs = 10
        files_per_dir = 100
        total_files = num_dirs * files_per_dir

        for d in range(num_dirs):
            subdir = tmp_path / f"batch_{d}"
            subdir.mkdir()
            for f in range(files_per_dir):
                file_path = subdir / f"file_{f}.txt"
                file_path.write_text(f"content {d}_{f}", encoding="utf-8")

        root = StorageRoot(
            root_name="bench_root",
            root_type=StorageRootType.LOCAL_DIR,
            uri_path=str(tmp_path),
            watch_mode=WatchMode.POLL,
        )

        scanner = LocalFilesystemScanner()
        start = time.perf_counter()
        nodes = [node async for node in scanner.scan_root(root, compute_sha256=False)]
        elapsed = time.perf_counter() - start

        return len(nodes), total_files, elapsed

    count, expected_total, elapsed = asyncio.run(_run())
    assert count == expected_total
    # Verify that scanning 1,000 files without full sha256 takes less than 2.0s
    assert elapsed < 2.0
