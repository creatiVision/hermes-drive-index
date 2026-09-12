"""
Unit tests for Subtree Profiler, Disruption Detection, NL Rules, and Tree-Diff.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hermes_auto_organizer.domain.profiler_models import (
    DisruptionType,
    FolderProfile,
    LifecycleDistribution,
    NaturalLanguageRule,
    OutlierItem,
    SolutionProposal,
)
from hermes_auto_organizer.infrastructure.storage.recursive_profiler import (
    RecursiveSubtreeProfiler,
)


def test_mime_entropy_calculation():
    # Completely homogeneous: single extension
    assert FolderProfile.calculate_mime_entropy({".pdf": 100}) == 0.0

    # Empty or single file
    assert FolderProfile.calculate_mime_entropy({}) == 0.0
    assert FolderProfile.calculate_mime_entropy({".txt": 1}) == 0.0

    # Perfectly uniform distribution across 4 extensions -> entropy should be exactly 1.0
    uniform = {".pdf": 10, ".docx": 10, ".jpg": 10, ".py": 10}
    entropy = FolderProfile.calculate_mime_entropy(uniform)
    assert pytest.approx(entropy, 0.01) == 1.0

    # Skewed distribution: 95% pdf, 5% txt -> low entropy
    skewed = {".pdf": 95, ".txt": 5}
    entropy_skewed = FolderProfile.calculate_mime_entropy(skewed)
    assert 0.0 < entropy_skewed < 0.5


def test_recursive_bottom_up_aggregation(tmp_path: Path):
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    profiler = RecursiveSubtreeProfiler(now=now)

    # Build folder structure:
    # tmp_path/
    # ├── root_doc.txt (direct)
    # └── sub1/
    #     ├── doc1.pdf
    #     └── sub2/
    #         └── script.py
    root_file = tmp_path / "root_doc.txt"
    root_file.write_text("hello root")

    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    pdf_file = sub1 / "doc1.pdf"
    pdf_file.write_text("pdf content")

    sub2 = sub1 / "sub2"
    sub2.mkdir()
    py_file = sub2 / "script.py"
    py_file.write_text("print('test')")

    profile = profiler.profile_directory(tmp_path)

    # Check root metrics
    assert profile.direct_files_count == 1
    assert profile.total_files_count == 3
    assert profile.direct_subdirs_count == 1
    assert profile.total_subdirs_count == 2
    assert profile.extension_counts.get(".txt") == 1
    assert profile.extension_counts.get(".pdf") == 1
    assert profile.extension_counts.get(".py") == 1

    # Check sub1 metrics
    child_sub1 = profile.subfolders[0]
    assert child_sub1.name == "sub1"
    assert child_sub1.direct_files_count == 1
    assert child_sub1.total_files_count == 2
    assert child_sub1.direct_subdirs_count == 1

    # Check sub2 metrics
    child_sub2 = child_sub1.subfolders[0]
    assert child_sub2.name == "sub2"
    assert child_sub2.direct_files_count == 1
    assert child_sub2.total_files_count == 1
    assert child_sub2.direct_subdirs_count == 0


def test_dump_zone_detection(tmp_path: Path):
    profiler = RecursiveSubtreeProfiler()

    # Create a chaotic dump zone folder with 20 files of 10 different extensions
    dump_dir = tmp_path / "DumpZone"
    dump_dir.mkdir()
    extensions = [".pdf", ".docx", ".zip", ".jpg", ".png", ".exe", ".iso", ".txt", ".csv", ".mp4"]
    for i in range(20):
        ext = extensions[i % len(extensions)]
        f = dump_dir / f"file_{i}{ext}"
        f.write_text(f"dummy data {i}")

    profile = profiler.profile_directory(dump_dir)
    assert profile.mime_entropy > 0.70
    assert profile.direct_files_count == 20

    disruptions = profiler.detect_disruptions(profile)
    types = [d.disruption_type for d in disruptions]
    assert DisruptionType.DUMP_ZONE in types


def test_outlier_code_project_in_downloads(tmp_path: Path):
    profiler = RecursiveSubtreeProfiler()

    # Create structure: Downloads / MyCoolRepo (with git and python files)
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir()
    repo_dir = downloads_dir / "MyCoolRepo"
    repo_dir.mkdir()
    git_dir = repo_dir / ".git"
    git_dir.mkdir()

    for i in range(6):
        (repo_dir / f"module_{i}.py").write_text("import sys")

    profile = profiler.profile_directory(downloads_dir, include_hidden=True)
    outliers = profiler.detect_outliers(profile)

    assert len(outliers) >= 1
    repo_outlier = next((o for o in outliers if "MyCoolRepo" in o.source_path), None)
    assert repo_outlier is not None
    assert repo_outlier.disruption_type == DisruptionType.TYPE_OUTLIER
    assert "Projekte" in repo_outlier.proposal.target_path
    assert repo_outlier.proposal.confidence > 0.85
    assert "Code-Projekt" in repo_outlier.reason_de


def test_natural_language_rules_synthesis(tmp_path: Path):
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    profiler = RecursiveSubtreeProfiler(now=now)

    # Create Downloads directory with old installers
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    # Create 5 installer files older than 90 days
    old_time = (now - timedelta(days=100)).timestamp()
    for i, ext in enumerate([".iso", ".dmg", ".deb", ".exe", ".msi"]):
        f = downloads / f"installer_{i}{ext}"
        f.write_text("installer data")
        import os
        os.utime(f, (old_time, old_time))

    profile = profiler.profile_directory(downloads)
    rules = profiler.synthesize_rules(profile)

    rule_ids = [r.id for r in rules]
    assert "rule-installers-purge" in rule_ids
    installer_rule = next(r for r in rules if r.id == "rule-installers-purge")
    assert "Installationsprogramme" in installer_rule.description_de
    assert installer_rule.affected_files_count == 5


def test_tree_diff_projection(tmp_path: Path):
    profiler = RecursiveSubtreeProfiler()

    # Setup profile
    root = tmp_path / "Workspace"
    root.mkdir()
    sub_project = root / "StandaloneProject"
    sub_project.mkdir()
    (sub_project / "app.py").write_text("print('hi')")

    profile = profiler.profile_directory(root)

    # Create outlier item and approve it
    outlier = OutlierItem(
        id="out-1",
        source_path=str(sub_project),
        disruption_type=DisruptionType.TYPE_OUTLIER,
        reason_de="Projekt verschieben",
        proposal=SolutionProposal(
            target_path=str(tmp_path / "Projekte" / "StandaloneProject"),
            confidence=0.9,
            reasoning_de="In Projektordner einsortieren",
            action_type="MOVE",
        ),
        status="approved",
    )

    diff_nodes = profiler.compute_tree_diff(
        profile=profile,
        confirmed_rules=[],
        resolved_outliers=[outlier],
    )

    moved_node = next((n for n in diff_nodes if n.source_path == str(sub_project)), None)
    assert moved_node is not None
    assert moved_node.action == "MOVE"
    assert moved_node.target_path == str(tmp_path / "Projekte" / "StandaloneProject")
    assert moved_node.is_outlier is True


def test_subtree_profiler_service_and_obsidian_export(tmp_path: Path):
    from hermes_auto_organizer.application.use_cases.subtree_profiler_service import SubtreeProfilerService

    # Setup test workspace
    workspace = tmp_path / "Workspace"
    workspace.mkdir()
    downloads = workspace / "Downloads"
    downloads.mkdir()
    (downloads / "document.pdf").write_text("dummy")

    service = SubtreeProfilerService()
    res = service.scan_and_profile(workspace)

    assert res["root_name"] == "Workspace"
    assert res["total_files"] == 1
    assert "synthesized_rules" in res

    # Test rule approval
    if service.rules:
        r_id = service.rules[0].id
        service.approve_rule(r_id, approved=True)
        assert service.rules[0].status == "approved"

    # Test Obsidian export
    vault_dir = tmp_path / "ObsidianVault"
    vault_dir.mkdir()
    index_path = service.export_to_obsidian(vault_dir)

    assert Path(index_path).exists()
    assert (vault_dir / "Auto-Organizer" / "Graph-Nodes" / "Downloads.md").exists()
    assert (vault_dir / "Auto-Organizer" / "Graph-Nodes" / "Workspace.md").exists()

    content = Path(index_path).read_text(encoding="utf-8")
    assert "LAN Storage Tree Graph Index" in content


def test_subtree_profiler_execution_and_rollback(tmp_path: Path):
    from hermes_auto_organizer.application.use_cases.subtree_profiler_service import SubtreeProfilerService

    workspace = tmp_path / "Workspace"
    workspace.mkdir()
    downloads = workspace / "Downloads"
    downloads.mkdir()
    target_projekte = tmp_path / "Projekte"

    # Create an outlier repo in Downloads
    repo = downloads / "MyRepo"
    repo.mkdir()
    (repo / "main.py").write_text("print(1)")
    (repo / ".git").mkdir()

    service = SubtreeProfilerService()
    service.scan_and_profile(workspace, include_hidden=True)

    # Resolve the outlier
    outliers = service.outliers
    assert len(outliers) >= 1
    outlier = outliers[0]
    target_dest = str(target_projekte / "MyRepo")
    service.resolve_outlier(outlier.id, status="approved", custom_target_path=target_dest)

    # Generate tree diff
    diff_nodes = service.generate_tree_diff()
    move_node = next((n for n in diff_nodes if n.source_path == str(repo)), None)
    assert move_node is not None
    assert move_node.action == "MOVE"
    assert move_node.target_path == target_dest

    # Execute tree diff
    exec_res = service.execute_tree_diff()
    assert exec_res["ok"] is True
    assert exec_res["executed_count"] >= 1
    assert Path(target_dest).exists()
    assert (Path(target_dest) / "main.py").exists()
    assert not repo.exists()

    # Rollback batch
    batch_id = exec_res["batch_id"]
    rb_res = service.rollback_batch(batch_id)
    assert rb_res["ok"] is True
    assert rb_res["reverted_count"] >= 1
    assert repo.exists()
    assert (repo / "main.py").exists()
    assert not Path(target_dest).exists()

