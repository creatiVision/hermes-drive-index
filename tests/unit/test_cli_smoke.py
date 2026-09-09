"""Offline CLI smoke tests (Phase E-8)."""

from __future__ import annotations

import json

import pytest

from hermes_drive_index import cli


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "hermes-drive-index" in capsys.readouterr().out


def test_status_reports_missing_db(tmp_path, monkeypatch, capsys):
    db = tmp_path / "nope.db"
    monkeypatch.setenv("HERMES_DRIVE_INDEX_DB_PATH", str(db))
    assert cli.main(["status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is False


def test_status_accepts_json_flag(tmp_path, monkeypatch, capsys):
    db = tmp_path / "nope.db"
    monkeypatch.setenv("HERMES_DRIVE_INDEX_DB_PATH", str(db))
    assert cli.main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is False


def test_doctor_reports_status_and_entry_points(tmp_path, monkeypatch, capsys):
    db = tmp_path / "nope.db"
    monkeypatch.setenv("HERMES_DRIVE_INDEX_DB_PATH", str(db))
    assert cli.main(["doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "hermes-drive-index"
    assert payload["status"]["exists"] is False


def test_ocr_flags_thread_to_config(tmp_path):
    args = cli.argparse.Namespace(
        config=None,
        root_folder_id=None,
        db_path=str(tmp_path / "index.db"),
        base_dir=None,
        ocr_enabled=True,
        ocr_image_enabled=True,
    )

    cfg = cli._config_from_args(args)

    assert cfg.ocr_enabled is True
    assert cfg.ocr_image_enabled is True


def test_cli_help_metavar_formatting(capsys):
    from hermes_auto_organizer.adapters import cli as auto_cli

    with pytest.raises(SystemExit):
        auto_cli.main(["ingest", "--help"])
    out = capsys.readouterr().out
    assert "--root PATH" in out
    assert "--name NAME" in out

    with pytest.raises(SystemExit):
        cli.main(["duplicates", "--help"])
    out = capsys.readouterr().out
    assert "FOLDER" in out


def test_cli_duplicates_and_cleanup_commands(tmp_path, capsys):
    (tmp_path / "junk.tmp").write_text("temp")
    (tmp_path / "pic.png").write_bytes(b"image")

    # duplicates
    assert cli.main(["duplicates", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "total_groups" in out

    # cleanup-old
    assert cli.main(["cleanup-old", str(tmp_path), "--days", "30"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "safe_deletion_candidates" in out

    # organize-downloads
    assert cli.main(["organize-downloads", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "planned_moves" in out

    # organize-documents
    assert cli.main(["organize-documents", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "folders_to_create" in out

    # organize-analyze
    assert cli.main(["organize-analyze", str(tmp_path), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["total_files"] == 2

    # organize-plan
    assert cli.main(["organize-plan", str(tmp_path), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "actions" in out

