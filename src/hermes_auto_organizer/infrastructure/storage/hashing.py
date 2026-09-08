"""
Two-tier content hashing engine for Hermes Auto-Organizer.
Implements Content-Hash Cache Pattern:
- Tier 1: Fast O(1) Probe: 4KB head + 4KB tail xxHash64 / fast hash
- Tier 2: Streamed 64KB chunked SHA-256 for exact content addressing

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

try:
    import xxhash
    _HAS_XXHASH = True
except ImportError:
    _HAS_XXHASH = False

CHUNK_SIZE = 65536  # 64 KB
PROBE_BLOCK_SIZE = 4096  # 4 KB


def compute_fast_probe_hash(path: Path) -> str:
    """
    Compute O(1) fast probe hash reading 4KB head and 4KB tail.
    Extremely fast for detecting file mutations without streaming the entire file.
    Optimized: Uses fstat on open descriptor to eliminate redundant path-based os.stat syscalls.
    """
    try:
        head_bytes = b""
        tail_bytes = b""
        with open(path, "rb") as f:
            size = os.fstat(f.fileno()).st_size
            head_bytes = f.read(PROBE_BLOCK_SIZE)
            if size > PROBE_BLOCK_SIZE:
                tail_offset = max(0, size - PROBE_BLOCK_SIZE)
                f.seek(tail_offset)
                tail_bytes = f.read(PROBE_BLOCK_SIZE)
    except (IsADirectoryError, PermissionError) as err:
        raise FileNotFoundError(f"File not found or unreadable: {path}") from err

    probe_data = head_bytes + tail_bytes
    if _HAS_XXHASH:
        return xxhash.xxh64(probe_data).hexdigest()
    return hashlib.sha256(probe_data).hexdigest()[:16]


def compute_full_sha256(path: Path) -> str:
    """
    Stream full SHA-256 of file contents in 64KB chunks.
    Ensures bounded memory consumption regardless of file size.
    Optimized: Avoids extra path-based os.stat check prior to open.
    """
    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IsADirectoryError, PermissionError) as err:
        raise FileNotFoundError(f"File not found or unreadable: {path}") from err
