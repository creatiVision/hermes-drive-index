"""
Public-data guardrails for committable repository files.

Modifications Copyright (c) 2026 creatiVision. Licensed under Apache 2.0.
Original Work Copyright (c) Gregory Horn and contributors.
"""

from __future__ import annotations

import os
import pathlib
import re

TEXT_EXTS = {".py", ".toml", ".md", ".yaml", ".yml", ".txt", ".example"}
BINARY_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SKIP_DIRS = {".git", ".local-test", ".pytest_cache", "__pycache__", ".venv", "venv"}
SECRET_FILENAME_RE = re.compile(r"(client_secret|credentials|token).*\.json$", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*=\s*['\"][^'\"]{12,}['\"]")
GENERIC_FORBIDDEN_PATTERNS = [
    re.compile(r"/home/gregory/\.hermes/drive_index/personal_files"),
]


def _private_patterns_from_env() -> list[str]:
    """Optional local-only validation patterns, not stored in the public repo."""
    raw = os.getenv("HERMES_DRIVE_INDEX_PRIVATE_GUARD_PATTERNS", "")
    return [item for item in raw.split(os.pathsep) if item]


def test_no_private_validation_values_or_databases_committed():
    root = pathlib.Path(__file__).resolve().parents[2]
    offenders = []
    local_private_patterns = _private_patterns_from_env()

    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or path.is_dir():
            continue
        rel = path.relative_to(root)
        if path.suffix in BINARY_SUFFIXES:
            offenders.append(f"database-like file present: {rel}")
            continue
        if SECRET_FILENAME_RE.search(path.name):
            offenders.append(f"secret-like JSON file present: {rel}")
            continue
        if path.suffix not in TEXT_EXTS and path.name != ".gitignore":
            continue

        text = path.read_text(errors="ignore")
        for pattern in GENERIC_FORBIDDEN_PATTERNS:
            if pattern.search(text):
                offenders.append(f"forbidden pattern {pattern.pattern!r} in {rel}")
        for match in SECRET_ASSIGNMENT_RE.finditer(text):
            offenders.append(f"secret-like assignment in {rel}: {match.group(1)}")
        for pattern in local_private_patterns:
            if pattern in text:
                offenders.append(f"local private pattern from env in {rel}")

    assert not offenders, "\n".join(offenders)
