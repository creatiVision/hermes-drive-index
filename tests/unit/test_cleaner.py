from __future__ import annotations

from pathlib import Path

from hermes_drive_index.core.cleaner import (
    classify_old_files,
    detect_duplicates,
    normalize_stem,
    plan_document_structure,
    plan_download_organization,
)
from hermes_drive_index.core.local_scanner import LocalFile


def test_normalize_stem():
    assert normalize_stem("report_final_v2") == "report"
    assert normalize_stem("invoice-copy(1)") == "invoice"
    assert normalize_stem("presentation_neu") == "presentation"


def test_detect_duplicates_exact_and_variants(tmp_path: Path):
    f1 = tmp_path / "doc.txt"
    f1.write_text("identical content")
    f2 = tmp_path / "doc_copy.txt"
    f2.write_text("identical content")

    f3 = tmp_path / "report_v1.txt"
    f3.write_text("draft v1")
    f4 = tmp_path / "report_final.txt"
    f4.write_text("final report text")

    files = [
        LocalFile("1", "doc.txt", "text/plain", str(f1), f1.stat().st_size, "2026-01-01T00:00:00+00:00", extension=".txt"),
        LocalFile("2", "doc_copy.txt", "text/plain", str(f2), f2.stat().st_size, "2026-01-02T00:00:00+00:00", extension=".txt"),
        LocalFile("3", "report_v1.txt", "text/plain", str(f3), f3.stat().st_size, "2026-01-01T00:00:00+00:00", extension=".txt"),
        LocalFile("4", "report_final.txt", "text/plain", str(f4), f4.stat().st_size, "2026-01-03T00:00:00+00:00", extension=".txt"),
    ]

    report = detect_duplicates(files)
    assert report["exact_duplicates_count"] == 1
    assert report["version_variants_count"] == 1
    assert report["total_reclaimable_bytes"] > 0


def test_classify_old_files():
    files = [
        LocalFile("1", "test.tmp", "application/octet-stream", "/tmp/test.tmp", 500, "2020-01-01T00:00:00+00:00", extension=".tmp"),
        LocalFile("2", "installer.deb", "application/vnd.debian.binary-package", "/downloads/installer.deb", 50000, "2025-01-01T00:00:00+00:00", extension=".deb"),
        LocalFile("3", "recent.pdf", "application/pdf", "/docs/recent.pdf", 2000, "2026-09-01T00:00:00+00:00", extension=".pdf"),
    ]
    res = classify_old_files(files, days_threshold=90)
    assert res["safe_deletion_candidates"]["count"] == 2
    assert res["active_files_count"] == 1


def test_plan_download_organization(tmp_path: Path):
    (tmp_path / "photo.jpg").write_bytes(b"image")
    (tmp_path / "invoice.pdf").write_bytes(b"doc")
    (tmp_path / "setup.deb").write_bytes(b"installer")

    res = plan_download_organization(tmp_path, by_date=False, detect_dupes=False)
    assert res["total_files"] == 3
    cats = res["categories_found"]
    assert "Images" in cats
    assert "Documents" in cats
    assert "Installers" in cats
    assert len(res["planned_moves"]) == 3


def test_plan_document_structure(tmp_path: Path):
    (tmp_path / "tax_rechnung_2025.pdf").write_bytes(b"invoice")
    (tmp_path / "client_project_spec.docx").write_bytes(b"project")

    res = plan_document_structure(tmp_path, detect_dupes=False)
    assert len(res["folders_to_create"]) >= 5
    moves = res["planned_moves"]
    assert len(moves) == 2
    dest_folders = {m["folder"] for m in moves}
    assert "02-Finances" in dest_folders
    assert "01-Projects" in dest_folders
