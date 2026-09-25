from __future__ import annotations

from pathlib import Path

from hermes_drive_index.core.local_scanner import (
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
