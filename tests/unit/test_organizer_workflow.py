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


def test_execute_on_approval_rejects_critical_system_paths(tmp_path: Path):
    from hermes_drive_index.core.organizer_workflow import (
        OrganizerAction,
        OrganizerPlan,
    )

    src_file = tmp_path / "normal.txt"
    src_file.write_text("safe")

    plan = OrganizerPlan(folder_path=str(tmp_path))
    plan.actions = [
        OrganizerAction(
            action_type="move",
            source=str(src_file),
            target="/etc/evil.txt",
        )
    ]

    exec_res = execute_on_approval(plan, dry_run=False)
    assert exec_res["success"] is False
    assert "Critical system path cannot be trashed" in exec_res["error"]
    assert src_file.exists()


def test_format_plan_presentation_relative_paths(tmp_path: Path):
    from hermes_drive_index.core.organizer_workflow import (
        OrganizerAction,
        OrganizerPlan,
    )

    plan = OrganizerPlan(folder_path=str(tmp_path))
    plan.actions = [
        OrganizerAction(
            action_type="create_folder",
            source=str(tmp_path / "Archives"),
            purpose="Archives",
        ),
        OrganizerAction(
            action_type="move",
            source=str(tmp_path / "file.txt"),
            target=str(tmp_path / "Archives" / "file.txt"),
        ),
        OrganizerAction(
            action_type="rename",
            source=str(tmp_path / "old.txt"),
            target=str(tmp_path / "new.txt"),
        ),
        OrganizerAction(
            action_type="delete",
            source=str(tmp_path / "temp.log"),
            purpose="Cleanup",
        ),
    ]
    pres = format_plan_presentation(plan)
    assert "📁 [CREATE FOLDER] `Archives/`" in pres
    assert "📦 [MOVE] `file.txt` ➔ `Archives/file.txt`" in pres
    assert "✏️ [RENAME] `old.txt` ➔ `new.txt`" in pres
    assert "🗑️ [DELETE/TRASH] `temp.log`" in pres
