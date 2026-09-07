"""
Unit tests for LocalFilesystemScanner.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import asyncio
from pathlib import Path

from hermes_auto_organizer.domain.models import StorageRoot, StorageRootType, WatchMode
from hermes_auto_organizer.infrastructure.storage.local_scanner import LocalFilesystemScanner


def test_local_scanner_discovers_files(tmp_path: Path):
    async def _run():
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        file_a = docs_dir / "plan.txt"
        file_a.write_text("Floor plan details", encoding="utf-8")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        ignored_file = git_dir / "config"
        ignored_file.write_text("git config", encoding="utf-8")

        root = StorageRoot(
            root_name="test_root",
            root_type=StorageRootType.LOCAL_DIR,
            uri_path=str(tmp_path),
            watch_mode=WatchMode.POLL,
        )

        scanner = LocalFilesystemScanner()
        return [node async for node in scanner.scan_root(root)]

    nodes = asyncio.run(_run())
    assert len(nodes) == 1
    assert nodes[0].file_name == "plan.txt"
    assert nodes[0].relative_path == "docs/plan.txt"
    assert nodes[0].content_sha256 is not None
