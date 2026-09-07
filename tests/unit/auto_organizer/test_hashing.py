"""
Unit tests for two-tier content hashing.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from pathlib import Path
import hashlib
from hermes_auto_organizer.infrastructure.storage.hashing import (
    compute_fast_probe_hash,
    compute_full_sha256,
)


def test_compute_full_sha256(tmp_path: Path):
    test_file = tmp_path / "hello.txt"
    content = b"Hello, Hermes Auto-Organizer!"
    test_file.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    actual = compute_full_sha256(test_file)
    assert actual == expected


def test_compute_fast_probe_hash_small_file(tmp_path: Path):
    test_file = tmp_path / "small.txt"
    test_file.write_bytes(b"Small content")

    fast_hash = compute_fast_probe_hash(test_file)
    assert isinstance(fast_hash, str)
    assert len(fast_hash) > 0


def test_compute_fast_probe_hash_large_file(tmp_path: Path):
    test_file = tmp_path / "large.bin"
    # Create 16KB file
    test_file.write_bytes(b"A" * 8192 + b"B" * 8192)

    fast_hash = compute_fast_probe_hash(test_file)
    assert isinstance(fast_hash, str)
    assert len(fast_hash) > 0
