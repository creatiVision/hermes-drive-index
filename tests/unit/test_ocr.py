
"""Optional OCR behavior tests."""

from __future__ import annotations
import pytest

import subprocess
from unittest import mock

from hermes_drive_index.config import default_config
from hermes_drive_index.core import extract, ocr
from hermes_drive_index.core import index as index_mod
from hermes_drive_index.core.index import index_file, init_db
from hermes_drive_index.core.models import DriveFile, is_indexable


def drive_file(mime_type: str = "application/pdf", name: str = "scan.pdf") -> DriveFile:
    return DriveFile(
        id="file-1",
        name=name,
        mime_type=mime_type,
        path=f"Personal Files/{name}",
        size=123,
        modified_time="2026-01-01T00:00:00Z",
        md5_checksum="abc",
        web_view_link="https://drive.example/file-1",
    )


def base_metrics() -> dict:
    return {
        "bytes_downloaded": 0,
        "chunks": 0,
        "files_indexed_native": 0,
        "files_indexed_ocr": 0,
        "files_metadata_only": 0,
        "ocr_attempted": 0,
        "ocr_failed": 0,
        "ocr_skipped_unavailable": 0,
    }


def test_ocr_module_detects_unavailable_tools(monkeypatch):
    monkeypatch.setattr(ocr.shutil, "which", lambda _cmd: None)

    assert ocr.ocr_available("pdf") is False
    assert ocr.ocr_available("image") is False


def test_ocr_disabled_by_default():
    cfg = default_config()

    assert cfg.ocr_enabled is False
    assert cfg.ocr_image_enabled is False


def test_ocr_not_attempted_when_disabled(tmp_path, monkeypatch):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF empty-ish")
    called = False
    monkeypatch.setattr(extract, "extract_pdf", lambda _path: "")

    def fake_ocr_pdf(_path):
        nonlocal called
        called = True
        return "ocr text"

    monkeypatch.setattr(extract, "ocr_pdf", fake_ocr_pdf)

    assert extract.extract_text(path, drive_file(), ocr_pdf_enabled=False) == ""
    assert called is False


def test_native_text_skips_ocr(tmp_path, monkeypatch):
    path = tmp_path / "native.pdf"
    path.write_bytes(b"%PDF native")
    called = False
    monkeypatch.setattr(extract, "extract_pdf", lambda _path: "native text")

    def fake_ocr_pdf(_path):
        nonlocal called
        called = True
        return "ocr text"

    monkeypatch.setattr(extract, "ocr_pdf", fake_ocr_pdf)

    assert extract.extract_text(path, drive_file(), ocr_pdf_enabled=True) == "native text"
    assert called is False


def test_scanned_pdf_ocr_when_enabled(tmp_path, monkeypatch):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF scan")
    monkeypatch.setattr(extract, "extract_pdf", lambda _path: "")
    monkeypatch.setattr(extract, "ocr_pdf", lambda _path, **_kwargs: "scanned invoice text")

    assert extract.extract_text(path, drive_file(), ocr_pdf_enabled=True) == "scanned invoice text"


def test_is_indexable_image_opt_in():
    png = drive_file("image/png", "scan.png")
    video = drive_file("video/mp4", "clip.mp4")

    assert is_indexable(png) is False
    assert is_indexable(png, ocr_image_enabled=True) is True
    assert is_indexable(video, ocr_image_enabled=True) is False


def test_index_file_status_indexed_ocr(tmp_path, monkeypatch):
    con = init_db(tmp_path / "index.db")
    local = tmp_path / "scan.pdf"
    local.write_bytes(b"pdf bytes")
    monkeypatch.setattr(index_mod, "download_or_export", lambda *_args: local)
    monkeypatch.setattr(index_mod, "extract_text", lambda *_args, **_kwargs: "ocr text")
    monkeypatch.setattr(index_mod, "text_was_ocr", lambda: True)
    metrics = base_metrics()

    index_file(con, object(), tmp_path, drive_file(), metrics, ocr_pdf_enabled=True)

    row = con.execute("select status, error from files where file_id='file-1'").fetchone()
    assert row == ("indexed_ocr", None)
    assert metrics["files_indexed_ocr"] == 1
    assert metrics["files_indexed_native"] == 0


def test_index_file_ocr_failure_is_nonblocking(tmp_path, monkeypatch):
    con = init_db(tmp_path / "index.db")
    local = tmp_path / "scan.pdf"
    local.write_bytes(b"pdf bytes")
    monkeypatch.setattr(index_mod, "download_or_export", lambda *_args: local)

    def raising_extract(*_args, **_kwargs):
        raise RuntimeError("ocr exploded")

    monkeypatch.setattr(index_mod, "extract_text", raising_extract)
    metrics = base_metrics()

    index_file(con, object(), tmp_path, drive_file(), metrics, ocr_pdf_enabled=True)

    row = con.execute("select status, error from files where file_id='file-1'").fetchone()
    assert row[0] == "indexed_metadata"
    assert "ocr failed" in row[1]
    assert metrics["ocr_failed"] == 1
    assert metrics["files_metadata_only"] == 1


def test_index_file_ocr_unavailable_skips_gracefully(tmp_path, monkeypatch):
    con = init_db(tmp_path / "index.db")
    local = tmp_path / "scan.pdf"
    local.write_bytes(b"pdf bytes")
    monkeypatch.setattr(index_mod, "download_or_export", lambda *_args: local)
    monkeypatch.setattr(index_mod, "extract_text", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(index_mod, "text_was_ocr", lambda: False)
    monkeypatch.setattr(index_mod, "ocr_available", lambda _kind: False)
    metrics = base_metrics()

    index_file(con, object(), tmp_path, drive_file(), metrics, ocr_pdf_enabled=True)

    row = con.execute("select status, error from files where file_id='file-1'").fetchone()
    assert row[0] == "indexed_metadata"
    assert "OCR tool unavailable" in row[1]
    assert metrics["ocr_skipped_unavailable"] == 1
    assert metrics["files_metadata_only"] == 1


def test_index_file_native_pdf_does_not_count_ocr_attempt(tmp_path, monkeypatch):
    con = init_db(tmp_path / "index.db")
    local = tmp_path / "native.pdf"
    local.write_bytes(b"pdf bytes")
    monkeypatch.setattr(index_mod, "download_or_export", lambda *_args: local)
    monkeypatch.setattr(index_mod, "ocr_available", lambda _kind: True)
    monkeypatch.setattr(index_mod, "extract_text", lambda *_args, **_kwargs: "native text")
    monkeypatch.setattr(index_mod, "text_was_ocr", lambda: False)
    metrics = base_metrics()

    index_file(con, object(), tmp_path, drive_file(name="native.pdf"), metrics, ocr_pdf_enabled=True)

    row = con.execute("select status from files where file_id='file-1'").fetchone()
    assert row[0] == "indexed"
    assert metrics["files_indexed_native"] == 1
    assert metrics["ocr_attempted"] == 0


def test_ocr_pdf_unavailable_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr, "ocr_available", lambda _kind: False)
    assert ocr.ocr_pdf(tmp_path / "scan.pdf") is None


def test_ocr_pdf_success(tmp_path):
    path = tmp_path / "scan.pdf"
    with (
        mock.patch.object(ocr, "ocr_available", return_value=True),
        mock.patch("subprocess.run") as mock_run,
        mock.patch("hermes_drive_index.core.extract.extract_pdf", return_value="  extracted pdf text  "),
    ):
        mock_run.return_value = subprocess.CompletedProcess(["ocrmypdf"], 0)
        result = ocr.ocr_pdf(path, timeout=60, extra_args=("--deskew",))

        assert result == "  extracted pdf text  "
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "ocrmypdf"
        assert "--deskew" in cmd
        assert str(path) in cmd
        assert kwargs["timeout"] == 60
        assert kwargs["check"] is True


def test_ocr_pdf_empty_text_returns_none(tmp_path):
    with (
        mock.patch.object(ocr, "ocr_available", return_value=True),
        mock.patch("subprocess.run"),
        mock.patch("hermes_drive_index.core.extract.extract_pdf", return_value="   \n  "),
    ):
        assert ocr.ocr_pdf(tmp_path / "scan.pdf") is None


def test_ocr_pdf_subprocess_exception_returns_none(tmp_path):
    with (
        mock.patch.object(ocr, "ocr_available", return_value=True),
        mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ocrmypdf")),
    ):
        assert ocr.ocr_pdf(tmp_path / "scan.pdf") is None


def test_ocr_pdf_timeout_returns_none(tmp_path):
    with (
        mock.patch.object(ocr, "ocr_available", return_value=True),
        mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ocrmypdf", timeout=120)),
    ):
        assert ocr.ocr_pdf(tmp_path / "scan.pdf") is None


def test_ocr_image_success(tmp_path):
    path = tmp_path / "scan.png"
    with (
        mock.patch.object(ocr, "ocr_available", return_value=True),
        mock.patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(["tesseract"], 0, stdout="image text\n")
        result = ocr.ocr_image(path, timeout=30, extra_args=("--dpi", "300", "-l", "eng+deu"))

        assert result == "image text\n"
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "tesseract"
        assert str(path) in cmd
        assert "--dpi" in cmd and "300" in cmd
        assert "-l" in cmd and "eng+deu" in cmd
        assert kwargs["timeout"] == 30


def test_ocr_extra_args_validation_rejects_unsafe():
    # Unsupported or injection flags should raise ValueError via validate_ocr_args
    with pytest.raises(ValueError, match="Unsupported Tesseract argument"):
        ocr.validate_ocr_args(["--config", "/etc/passwd"], ocr._SAFE_TESSERACT_FLAGS, ocr._SAFE_TESSERACT_FLAGS_WITH_VALUES, "Tesseract")

    with pytest.raises(ValueError, match="Unsupported Tesseract value"):
        ocr.validate_ocr_args(["--dpi", "../etc/passwd"], ocr._SAFE_TESSERACT_FLAGS, ocr._SAFE_TESSERACT_FLAGS_WITH_VALUES, "Tesseract")

    with pytest.raises(ValueError, match="Unsupported OCRmyPDF argument"):
        ocr.validate_ocr_args(["--sidecar", "/tmp/out.txt"], ocr._SAFE_OCRMYPDF_FLAGS, ocr._SAFE_OCRMYPDF_FLAGS_WITH_VALUES, "OCRmyPDF")


def test_ocr_pdf_rejects_unsafe_extra_args(tmp_path):
    path = tmp_path / "scan.pdf"
    with mock.patch.object(ocr, "ocr_available", return_value=True):
        # ocr_pdf catches Exception and returns None when validate_ocr_args raises ValueError
        assert ocr.ocr_pdf(path, extra_args=("--sidecar", "/tmp/out.txt")) is None


def test_ocr_image_rejects_unsafe_extra_args(tmp_path):
    path = tmp_path / "scan.png"
    with mock.patch.object(ocr, "ocr_available", return_value=True):
        # ocr_image catches Exception and returns None when validate_ocr_args raises ValueError
        assert ocr.ocr_image(path, extra_args=("--config", "/etc/passwd")) is None
