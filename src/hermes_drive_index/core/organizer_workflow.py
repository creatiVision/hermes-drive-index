"""Complete interactive File Organizer workflow engine following SKILL.md specification.

Implements the 7-step sequence:
1. Intent Check
2. Access Check
3. Analyse First
4. Propose a Plan
5. Wait for Explicit Approval
6. Execute on Approval (Folders -> Move -> Rename -> Delete/Trash)
7. Dry-run Mode
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
from typing import Sequence

from .cleaner import EXT_TO_CATEGORY, detect_duplicates
from .local_scanner import LocalFile, safe_trash, scan_local_directory

APPROVAL_KEYWORDS = {
    "approve",
    "go ahead",
    "yes",
    "do it",
    "execute",
    "run it",
    "proceed",
    "ja",
    "mach es",
    "ausführen",
}

DISQUALIFIERS = ["but", "maybe", "wait", "?", "aber", "vielleicht", "warte", "noch nicht"]


@dataclass
class OrganizerAction:
    action_type: str  # "create_folder", "move", "rename", "delete"
    source: str
    target: str | None = None
    purpose: str = ""
    status: str = "pending"  # "pending", "success", "failed"
    error: str | None = None


@dataclass
class OrganizerPlan:
    folder_path: str
    actions: list[OrganizerAction] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dry_run: bool = True
    executed: bool = False
    counts: dict[str, int] = field(default_factory=lambda: {
        "renamed": 0,
        "moved": 0,
        "folders_created": 0,
        "deleted": 0,
    })


def intent_check(user_message: str, folder_path: str | None = None) -> dict:
    """Step 1: Check intent.

    If message is vague or folder is missing, ask what the user wants to accomplish and which folder.
    """
    msg = (user_message or "").strip().lower()
    vague_phrases = {"hi", "hello", "hey", "help", "organize", "clean", "cleanup"}
    is_vague = msg in vague_phrases or len(msg.split()) <= 1

    if is_vague or not folder_path:
        needs = []
        if not folder_path:
            needs.append("which folder you want to organize")
        if is_vague:
            needs.append("what specific goal you are trying to accomplish (e.g., sort downloads, find duplicates, clean old files)")
        return {
            "proceed": False,
            "message": f"To begin organizing, please specify: {', and '.join(needs)}.",
            "prompt_user": True,
        }
    return {
        "proceed": True,
        "folder_path": folder_path,
        "message": "Intent confirmed.",
    }


def access_check(folder_path: Path | str) -> dict:
    """Step 2: Tell the user what folders can and cannot be reached."""
    p = Path(folder_path).expanduser().resolve()
    if not p.exists():
        return {
            "accessible": False,
            "folder_path": str(p),
            "reason": f"Path '{p}' does not exist.",
            "suggestion": "Please ensure the path is correct and mounted.",
        }
    if not p.is_dir():
        return {
            "accessible": False,
            "folder_path": str(p),
            "reason": f"Path '{p}' is a file, not a folder.",
            "suggestion": "Please supply a directory path.",
        }
    readable = os.access(p, os.R_OK)
    writable = os.access(p, os.W_OK)

    if not (readable and writable):
        perms = []
        if not readable:
            perms.append("read")
        if not writable:
            perms.append("write")
        return {
            "accessible": False,
            "folder_path": str(p),
            "reason": f"Insufficient permissions: missing {', '.join(perms)} access.",
            "suggestion": "Please adjust folder permissions (e.g. chmod / chown) before proceeding.",
        }

    return {
        "accessible": True,
        "folder_path": str(p),
        "readable": readable,
        "writable": writable,
    }


def analyse_first(folder_path: Path | str) -> dict:
    """Step 3: Walk the folder and report scannable summary BEFORE proposing anything:

    - total file count and size
    - deepest nesting
    - current naming patterns
    - potential duplicates (same name / same size)
    - orphan and unclear files
    - groupings by file type
    """
    base = Path(folder_path).expanduser().resolve()
    files = scan_local_directory(base, recursive=True, compute_hashes=True)

    total_count = len(files)
    total_size = sum(f.size for f in files)

    # Deepest nesting
    max_nesting = 0
    type_groups: dict[str, list[LocalFile]] = defaultdict(list)
    naming_patterns: Counter[str] = Counter()
    unclear_files: list[str] = []

    for f in files:
        rel_p = Path(f.path).relative_to(base)
        nesting = len(rel_p.parts) - 1
        if nesting > max_nesting:
            max_nesting = nesting

        cat = EXT_TO_CATEGORY.get(f.extension, "Other")
        type_groups[cat].append(f)

        # Naming pattern analysis
        stem = Path(f.name).stem
        if re.search(r"^\d{4}[-_]\d{2}[-_]\d{2}", stem):
            naming_patterns["date_prefixed (YYYY-MM-DD_*)"] += 1
        elif re.search(r"[_\- ]v\d+", stem, re.IGNORECASE):
            naming_patterns["version_tagged (*_v1, *_v2)"] += 1
        elif re.search(r"[_\- ](copy|kopie|\(\d+\))", stem, re.IGNORECASE):
            naming_patterns["copy_annotated (*_copy, *(1))"] += 1
        elif "_" in stem:
            naming_patterns["snake_case"] += 1
        elif "-" in stem:
            naming_patterns["kebab_case"] += 1
        elif " " in stem:
            naming_patterns["spaced_names"] += 1
        else:
            naming_patterns["simple_word"] += 1

        # Unclear or orphan files (random hash, untyped, weird characters)
        if (
            len(stem) > 30 and re.match(r"^[a-f0-9]+$", stem)
            or f.extension == ""
            or re.search(r"^[~#%&]", f.name)
        ):
            unclear_files.append(f.name)

    # Duplicates check
    dupes_report = detect_duplicates(files)

    # Markdown summary
    summary_lines = [
        f"### Folder Analysis for: `{base}`",
        f"- **Total Files**: {total_count} files ({round(total_size / (1024 * 1024), 2)} MB)",
        f"- **Deepest Nesting**: {max_nesting} levels below root",
        "",
        "#### Groupings by File Type:",
    ]
    for cat, flist in sorted(type_groups.items(), key=lambda x: -len(x[1])):
        cat_size = sum(x.size for x in flist)
        summary_lines.append(f"- **{cat}**: {len(flist)} files ({round(cat_size / (1024 * 1024), 2)} MB)")

    summary_lines.append("")
    summary_lines.append("#### Naming Patterns Detected:")
    for pat, count in naming_patterns.most_common():
        summary_lines.append(f"- {pat}: {count} files")

    if dupes_report["total_groups"] > 0:
        summary_lines.append("")
        summary_lines.append(f"#### Potential Duplicates: {dupes_report['total_groups']} groups ({dupes_report['total_reclaimable_mb']} MB reclaimable)")
        summary_lines.append(f"- Exact duplicates: {dupes_report['exact_duplicates_count']} groups")
        summary_lines.append(f"- Version variants: {dupes_report['version_variants_count']} groups")

    if unclear_files:
        summary_lines.append("")
        summary_lines.append(f"#### Unclear / Ambiguous Files ({len(unclear_files)}):")
        for u in unclear_files[:8]:
            summary_lines.append(f"- `{u}`")
        if len(unclear_files) > 8:
            summary_lines.append(f"- ...and {len(unclear_files) - 8} more")

    return {
        "folder_path": str(base),
        "total_files": total_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "deepest_nesting": max_nesting,
        "type_groups": {k: len(v) for k, v in type_groups.items()},
        "naming_patterns": dict(naming_patterns),
        "unclear_files": unclear_files,
        "duplicates": dupes_report,
        "markdown_summary": "\n".join(summary_lines),
    }


def propose_plan(
    folder_path: Path | str,
    *,
    organize_mode: str = "downloads",  # "downloads", "documents", or "cleanup"
    custom_rules: Sequence[dict] | None = None,
) -> OrganizerPlan:
    """Step 4: Propose a concrete plan with before-to-after mapping.

    Totals at top: "X renamed, Y moved, Z folders created, W deleted".
    """
    base = Path(folder_path).expanduser().resolve()
    files = scan_local_directory(base, recursive=organize_mode != "downloads")

    plan = OrganizerPlan(folder_path=str(base))
    created_folders: set[str] = set()

    if organize_mode == "downloads":
        # Group flat files by category
        for f in files:
            if f.is_dir:
                continue
            cat = EXT_TO_CATEGORY.get(f.extension, "Other")
            dest_dir = base / cat
            if str(dest_dir) not in created_folders and not dest_dir.exists():
                created_folders.add(str(dest_dir))
                plan.actions.append(
                    OrganizerAction(
                        action_type="create_folder",
                        source=str(dest_dir),
                        purpose=f"Destination for {cat} files",
                    )
                )

            dest_path = dest_dir / f.name
            if dest_path != Path(f.path):
                plan.actions.append(
                    OrganizerAction(
                        action_type="move",
                        source=f.path,
                        target=str(dest_path),
                        purpose=f"Move {cat} file into {cat}/",
                    )
                )

    elif organize_mode == "documents":
        # Propose standard 5 top-level folders
        standard_dirs = ["01-Projects", "02-Finances", "03-Personal", "04-Reference", "05-Archive"]
        for s in standard_dirs:
            p = base / s
            if not p.exists() and str(p) not in created_folders:
                created_folders.add(str(p))
                plan.actions.append(
                    OrganizerAction(
                        action_type="create_folder",
                        source=str(p),
                        purpose=f"Top-level category {s}",
                    )
                )

        from .cleaner import plan_document_structure
        doc_plan = plan_document_structure(base, detect_dupes=False)
        for move in doc_plan["planned_moves"]:
            if move["source_path"] != move["target_path"]:
                plan.actions.append(
                    OrganizerAction(
                        action_type="move",
                        source=move["source_path"],
                        target=move["target_path"],
                        purpose=f"Classify into {move['folder']}",
                    )
                )

    # Recalculate totals
    plan.counts["folders_created"] = sum(1 for a in plan.actions if a.action_type == "create_folder")
    plan.counts["moved"] = sum(1 for a in plan.actions if a.action_type == "move")
    plan.counts["renamed"] = sum(1 for a in plan.actions if a.action_type == "rename")
    plan.counts["deleted"] = sum(1 for a in plan.actions if a.action_type == "delete")

    return plan


def format_plan_presentation(plan: OrganizerPlan) -> str:
    """Format the plan presentation with clear icons and readable paths."""
    base_path = Path(plan.folder_path)

    def _rel(p_str: str | None) -> str:
        if not p_str:
            return ""
        try:
            return str(Path(p_str).relative_to(base_path))
        except ValueError:
            return p_str

    lines = [
        f"📋 **Summary Totals**: {plan.counts['renamed']} renamed, {plan.counts['moved']} moved, "
        f"{plan.counts['folders_created']} folders created, {plan.counts['deleted']} deleted",
        "",
        "### 🎯 Proposed Actions:",
    ]
    for i, a in enumerate(plan.actions[:30], 1):
        if a.action_type == "create_folder":
            lines.append(f"{i}. 📁 [CREATE FOLDER] `{_rel(a.source)}/` ({a.purpose})")
        elif a.action_type == "move":
            lines.append(f"{i}. 📦 [MOVE] `{Path(a.source).name}` ➔ `{_rel(a.target)}`")
        elif a.action_type == "rename":
            lines.append(f"{i}. ✏️ [RENAME] `{Path(a.source).name}` ➔ `{Path(a.target or '').name}`")
        elif a.action_type == "delete":
            lines.append(f"{i}. 🗑️ [DELETE/TRASH] `{_rel(a.source)}` ({a.purpose})")

    if len(plan.actions) > 30:
        lines.append(f"... and {len(plan.actions) - 30} more actions.")

    lines.append("")
    lines.append(
        "💡 *This is a proposal - nothing has been changed on disk yet.*\n"
        "Reply **'approve'** or **'go ahead'** to execute, or specify adjustments."
    )
    return "\n".join(lines)


def validate_approval(user_response: str) -> bool:
    """Step 5: Check explicit approval.

    Approval = "approve" / "go ahead" / "yes" / "do it" / "execute" / "run it" / "proceed".
    Anything with "but", "maybe", "wait", or a question mark is NOT approval.
    """
    resp = (user_response or "").strip().lower()

    # If any disqualifier is present, it is not approval
    for disq in DISQUALIFIERS:
        if disq in resp:
            return False

    # Check if contains any approval keyword
    for kw in APPROVAL_KEYWORDS:
        # Match as whole word or phrase
        if re.search(r"\b" + re.escape(kw) + r"\b", resp):
            return True

    return False


def execute_on_approval(
    plan: OrganizerPlan,
    *,
    dry_run: bool = False,
    batch_size: int = 50,
) -> dict:
    """Step 6: Execute on approval in strict order:

    1. Create folders
    2. Move files
    3. Rename files
    4. Delete files (via safe_trash)

    Reports progress in batches. If any operation fails, STOP, report, and summarize.
    """
    if dry_run:
        return {
            "executed": False,
            "dry_run": True,
            "message": "Dry-run mode: confirmed no files changed.",
            "actions_planned": len(plan.actions),
        }

    # Partition actions in required order
    action_order = ["create_folder", "move", "rename", "delete"]
    sorted_actions: list[OrganizerAction] = []
    for atype in action_order:
        sorted_actions.extend([a for a in plan.actions if a.action_type == atype])

    executed_counts = {"folders_created": 0, "moved": 0, "renamed": 0, "deleted": 0}
    failed_action: OrganizerAction | None = None
    untouched_actions: list[OrganizerAction] = []

    for idx, act in enumerate(sorted_actions):
        try:
            if act.action_type == "create_folder":
                p = Path(act.source)
                p.mkdir(parents=True, exist_ok=True)
                act.status = "success"
                executed_counts["folders_created"] += 1

            elif act.action_type in {"move", "rename"}:
                src = Path(act.source)
                tgt = Path(act.target or "")
                tgt.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(tgt))
                act.status = "success"
                if act.action_type == "move":
                    executed_counts["moved"] += 1
                else:
                    executed_counts["renamed"] += 1

            elif act.action_type == "delete":
                safe_trash(act.source)
                act.status = "success"
                executed_counts["deleted"] += 1

        except Exception as exc:
            act.status = "failed"
            act.error = str(exc)
            failed_action = act
            untouched_actions = sorted_actions[idx + 1:]
            break

    plan.executed = True

    if failed_action:
        return {
            "success": False,
            "error": f"Operation failed on {failed_action.source}: {failed_action.error}",
            "failed_action": asdict(failed_action),
            "executed_counts": executed_counts,
            "untouched_count": len(untouched_actions),
            "untouched_actions": [asdict(a) for a in untouched_actions[:20]],
        }

    return {
        "success": True,
        "executed_counts": executed_counts,
        "total_executed": sum(executed_counts.values()),
        "summary": (
            f"Execution completed: {executed_counts['folders_created']} folders created, "
            f"{executed_counts['moved']} files moved, {executed_counts['renamed']} files renamed, "
            f"{executed_counts['deleted']} files moved to trash."
        ),
    }
