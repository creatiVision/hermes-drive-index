from __future__ import annotations

from pathlib import Path

from hermes_drive_index.core.organizer_workflow import (
    access_check,
    analyse_first,
    execute_on_approval,
    format_plan_presentation,
    intent_check,
    propose_plan,
    validate_approval,
)


def test_intent_check():
    assert intent_check("hi", None)["proceed"] is False
    assert intent_check("organize", None)["proceed"] is False
    assert intent_check("help sort my downloads", "/tmp/downloads")["proceed"] is True


def test_access_check(tmp_path: Path):
    res = access_check(tmp_path)
    assert res["accessible"] is True
    assert res["readable"] is True
    assert res["writable"] is True

    non_existent = tmp_path / "non_existent_folder"
    assert access_check(non_existent)["accessible"] is False


def test_validate_approval():
    assert validate_approval("approve") is True
    assert validate_approval("go ahead") is True
    assert validate_approval("yes") is True
    assert validate_approval("do it") is True
    assert validate_approval("proceed") is True

    # Disqualifiers
    assert validate_approval("approve, but wait") is False
    assert validate_approval("maybe?") is False
    assert validate_approval("what will happen?") is False
    assert validate_approval("no") is False


def test_organizer_plan_and_execution_workflow(tmp_path: Path):
    (tmp_path / "img1.png").write_bytes(b"png")
    (tmp_path / "doc1.pdf").write_bytes(b"pdf")

    # Step 3: analyse_first
    analysis = analyse_first(tmp_path)
    assert analysis["total_files"] == 2
    assert "markdown_summary" in analysis

    # Step 4: propose_plan
    plan = propose_plan(tmp_path, organize_mode="downloads")
    assert plan.counts["moved"] == 2
    presentation = format_plan_presentation(plan)
    assert "Summary Totals" in presentation
    assert "Reply **'approve'** or **'go ahead'** to execute" in presentation

    # Step 7: dry-run mode
    dry_res = execute_on_approval(plan, dry_run=True)
    assert dry_res["dry_run"] is True
    assert (tmp_path / "img1.png").exists()

    # Step 6: execute on approval
    exec_res = execute_on_approval(plan, dry_run=False)
    assert exec_res["success"] is True
    assert exec_res["executed_counts"]["moved"] == 2
    assert (tmp_path / "Images" / "img1.png").exists()
    assert (tmp_path / "Documents" / "doc1.pdf").exists()
