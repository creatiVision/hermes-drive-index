from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from hermes_drive_index.core.local_scanner import (
    compute_file_hashes,
    guess_mime_type,
    safe_trash,
    scan_local_directory,
)


def test_guess_mime_type():
    assert guess_mime_type("test.md") == "text/markdown"
    assert guess_mime_type("test.pdf") == "application/pdf"
    assert guess_mime_type("test.deb") == "application/vnd.debian.binary-package"
    assert guess_mime_type("test.unknownext123") == "application/octet-stream"


def test_scan_local_directory(tmp_path: Path):
    d1 = tmp_path / "sub"
    d1.mkdir()
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello world")
    f2 = d1 / "file2.pdf"
    f2.write_bytes(b"%PDF-1.4 test")

    files = scan_local_directory(tmp_path, recursive=True, compute_hashes=True)
    assert len(files) == 2
    names = {f.name for f in files}
    assert names == {"file1.txt", "file2.pdf"}

    pdf_file = next(f for f in files if f.name == "file2.pdf")
    assert pdf_file.size > 0
    assert pdf_file.md5_checksum is not None
    assert pdf_file.sha256_checksum is not None
    assert pdf_file.web_view_link.startswith("file://")


def test_safe_trash(tmp_path: Path):
    target = tmp_path / "trash_candidate.tmp"
    target.write_text("temporary content")
    assert target.exists()

    res = safe_trash(target)
    assert res is True
    assert not target.exists()


def test_safe_trash_exception_and_failure_logging(tmp_path: Path, monkeypatch, caplog):
    import logging
    import shutil
    import subprocess

    target = tmp_path / "trash_candidate.tmp"
    target.write_text("temporary content")

    # Mock shutil.which to pretend gio and trash are present
    monkeypatch.setattr(shutil, "which", lambda cmd: f"/fake/bin/{cmd}")

    def fake_run(cmd, capture_output=True, text=True, check=False):
        if "gio" in cmd[0]:
            raise OSError("gio binary execution error")
        elif "trash" in cmd[0]:
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="trash command failed")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with caplog.at_level(logging.DEBUG):
        res = safe_trash(target)

    assert res is True
    assert not target.exists()
    assert "gio trash command failed: gio binary execution error" in caplog.text
    assert "trash-put failed with returncode 1: trash command failed" in caplog.text


def test_compute_file_hashes_basic(tmp_path: Path):
    content = b"hello world 123"
    test_file = tmp_path / "sample.txt"
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    expected_sha256 = hashlib.sha256(content).hexdigest()

    # Test with Path object
    md5, sha256 = compute_file_hashes(test_file)
    assert md5 == expected_md5
    assert sha256 == expected_sha256

    # Test with string path
    md5_str, sha256_str = compute_file_hashes(str(test_file))
    assert md5_str == expected_md5
    assert sha256_str == expected_sha256


def test_compute_file_hashes_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")

    expected_md5 = hashlib.md5(b"").hexdigest()
    expected_sha256 = hashlib.sha256(b"").hexdigest()

    md5, sha256 = compute_file_hashes(empty_file)
    assert md5 == expected_md5
    assert sha256 == expected_sha256


def test_compute_file_hashes_custom_chunk_size(tmp_path: Path):
    content = b"A" * 100
    test_file = tmp_path / "chunks.txt"
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    expected_sha256 = hashlib.sha256(content).hexdigest()

    # Read with chunk size smaller than content length to test iteration
    md5, sha256 = compute_file_hashes(test_file, chunk_size=10)
    assert md5 == expected_md5
    assert sha256 == expected_sha256


def test_compute_file_hashes_nonexistent_file(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.txt"
    with pytest.raises(FileNotFoundError):
        compute_file_hashes(non_existent)
