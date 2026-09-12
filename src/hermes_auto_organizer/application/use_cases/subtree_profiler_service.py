"""
Application Service for Subtree Profiling, Disruption Diagnostics,
NL Rule Approval, Outlier Triage, and Tree-Diff Projection.

Orchestrates domain models and infrastructure adapters following Hexagonal Architecture.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

try:
    from send2trash import send2trash
    _HAS_SEND2TRASH = True
except ImportError:
    _HAS_SEND2TRASH = False

from hermes_auto_organizer.application.ports.profiler_port import SubtreeProfilerPort
from hermes_auto_organizer.domain.models import (
    ExecutionRecord,
    MoveIntent,
    OperationType,
    RollbackState,
)
from hermes_auto_organizer.domain.policies import DiskCleaningPolicy
from hermes_auto_organizer.domain.profiler_models import (
    DisruptionItem,
    FolderProfile,
    NaturalLanguageRule,
    OutlierItem,
    TreeDiffNode,
)
from hermes_auto_organizer.infrastructure.obsidian.extended_graph_exporter import (
    ObsidianExtendedGraphExporter,
)
from hermes_auto_organizer.infrastructure.storage.atomic_runner import (
    AtomicExecutionRunner,
)
from hermes_auto_organizer.infrastructure.storage.recursive_profiler import (
    RecursiveSubtreeProfiler,
)

logger = logging.getLogger("hermes.auto_organizer.profiler_service")


class SubtreeProfilerService:
    """Orchestrates recursive profiling, disruption analysis, rules, and tree-diff projection."""

    def __init__(self, profiler: Optional[SubtreeProfilerPort] = None) -> None:
        self._profiler = profiler or RecursiveSubtreeProfiler()
        self._current_node_id: str = "laptop"
        self._current_profile: Optional[FolderProfile] = None
        self._disruptions: List[DisruptionItem] = []
        self._outliers: List[OutlierItem] = []
        self._rules: List[NaturalLanguageRule] = []
        self._execution_history: Dict[UUID, List[ExecutionRecord]] = {}

    @property
    def current_node_id(self) -> str:
        return self._current_node_id

    @property
    def current_profile(self) -> Optional[FolderProfile]:
        return self._current_profile

    @property
    def disruptions(self) -> List[DisruptionItem]:
        return self._disruptions

    @property
    def outliers(self) -> List[OutlierItem]:
        return self._outliers

    @property
    def rules(self) -> List[NaturalLanguageRule]:
        return self._rules

    def scan_and_profile(
        self,
        path: Path | str,
        node_id: str = "laptop",
        max_depth: int = 8,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """Scans path recursively, profiles subtrees, finds outliers and synthesizes rules."""
        self._current_node_id = (node_id or "laptop").strip()

        if self._current_node_id not in ("laptop", "local", "localhost"):
            from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import SSHNodeInspector
            ssh_inspector = SSHNodeInspector()
            profile = ssh_inspector.profile_remote_subtree(
                node_id=self._current_node_id,
                remote_path=str(path),
                max_depth=max_depth,
                include_hidden=include_hidden,
            )
        else:
            profile = self._profiler.profile_directory(path, max_depth=max_depth, include_hidden=include_hidden)

        disruptions = self._profiler.detect_disruptions(profile)
        outliers = self._profiler.detect_outliers(profile)
        rules = self._profiler.synthesize_rules(profile)

        self._current_profile = profile
        self._disruptions = disruptions
        self._outliers = outliers
        self._rules = rules

        return {
            "node_id": self._current_node_id,
            "root_path": profile.path,
            "root_name": profile.name,
            "total_files": profile.total_files_count,
            "total_bytes": profile.total_bytes,
            "total_subdirs": profile.total_subdirs_count,
            "mime_entropy": round(profile.mime_entropy, 3),
            "dominant_extension": profile.dominant_extension,
            "disruptions_count": len(disruptions),
            "outliers_count": len(outliers),
            "rules_count": len(rules),
            "disruptions": [asdict(d) for d in disruptions[:50]],
            "outliers": [asdict(o) for o in outliers],
            "synthesized_rules": [asdict(r) for r in rules],
        }

    def approve_rule(self, rule_id: str, approved: bool = True) -> bool:
        """Approve or reject a synthesized natural language meta-rule."""
        for i, rule in enumerate(self._rules):
            if rule.id == rule_id:
                new_status = "approved" if approved else "rejected"
                self._rules[i] = NaturalLanguageRule(
                    id=rule.id,
                    title_de=rule.title_de,
                    description_de=rule.description_de,
                    condition_json=rule.condition_json,
                    target_path_template=rule.target_path_template,
                    affected_files_count=rule.affected_files_count,
                    affected_bytes=rule.affected_bytes,
                    confidence=rule.confidence,
                    status=new_status,
                )
                return True
        return False

    def resolve_outlier(
        self,
        outlier_id: str,
        status: str,  # "approved", "rejected", "customized"
        custom_target_path: Optional[str] = None,
    ) -> bool:
        """Human-in-the-loop triage for an individual outlier."""
        for i, out in enumerate(self._outliers):
            if out.id == outlier_id:
                self._outliers[i] = OutlierItem(
                    id=out.id,
                    source_path=out.source_path,
                    disruption_type=out.disruption_type,
                    reason_de=out.reason_de,
                    proposal=out.proposal,
                    status=status,
                    custom_target_path=custom_target_path or out.custom_target_path,
                )
                return True
        return False

    def generate_tree_diff(self) -> List[TreeDiffNode]:
        """Projects S_ideal from S_now using confirmed rules and resolved outliers."""
        if not self._current_profile:
            return []

        approved_rules = [r for r in self._rules if r.status == "approved"]
        return self._profiler.compute_tree_diff(
            profile=self._current_profile,
            confirmed_rules=approved_rules,
            resolved_outliers=self._outliers,
        )

    def export_to_obsidian(self, vault_path: Path | str) -> str:
        """Exports currently analyzed tree and diff to Obsidian for Extended Graph visualization."""
        if not self._current_profile:
            raise ValueError("No profile available. Run scan_and_profile first.")

        diff_nodes = self.generate_tree_diff()
        exporter = ObsidianExtendedGraphExporter(vault_path)
        index_path = exporter.export_graph(
            root_profile=self._current_profile,
            diff_nodes=diff_nodes,
            outliers=self._outliers,
        )
        return str(index_path)

    def execute_tree_diff(
        self,
        batch_id: Optional[UUID] = None,
        only_approved: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes projected operations from the Tree-Diff (MOVE, ARCHIVE, CLEAN_TEMP)
        with zero-data-loss trash safety, safe path validation, and transaction journaling.
        """
        batch_uuid = batch_id or uuid4()
        diff_nodes = self.generate_tree_diff()

        executed: List[ExecutionRecord] = []
        errors: List[Dict[str, str]] = []

        is_remote = self._current_node_id not in ("laptop", "local", "localhost")

        for node in diff_nodes:
            if node.action not in ("MOVE", "ARCHIVE", "CLEAN_TEMP"):
                continue

            if is_remote:
                try:
                    rec = self._execute_remote_node(node, batch_uuid)
                    if rec:
                        executed.append(rec)
                except Exception as e:
                    logger.error("Failed remote execute tree-diff node %s -> %s: %s", node.source_path, node.target_path, e)
                    errors.append({"source": node.source_path, "error": str(e)})
                continue

            src = Path(node.source_path)
            if not src.exists():
                continue

            try:
                DiskCleaningPolicy.assert_cleanup_safe(str(src))

                if node.action == "CLEAN_TEMP":
                    if _HAS_SEND2TRASH:
                        send2trash(str(src))
                    else:
                        trash_dir = src.parent / ".hermes_trash"
                        trash_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), str(trash_dir / src.name))

                    rec = ExecutionRecord(
                        id=uuid4(),
                        batch_id=batch_uuid,
                        source_path=str(src),
                        destination_path=f"trash://{src.name}",
                        operation_type=OperationType.TRASH_DELETE,
                        rollback_state=RollbackState.EXECUTED,
                        executed_at=datetime.now(timezone.utc),
                    )
                    executed.append(rec)

                elif node.action in ("MOVE", "ARCHIVE"):
                    if not node.target_path:
                        continue
                    dst = Path(node.target_path)
                    if src.resolve() == dst.resolve():
                        continue

                    DiskCleaningPolicy.assert_cleanup_safe(str(dst.parent))
                    dst.parent.mkdir(parents=True, exist_ok=True)

                    if src.is_dir():
                        is_cross_device = False
                        try:
                            is_cross_device = src.stat().st_dev != dst.parent.stat().st_dev
                        except OSError:
                            pass

                        if is_cross_device:
                            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
                            if _HAS_SEND2TRASH:
                                send2trash(str(src))
                            else:
                                shutil.rmtree(str(src))
                            op_type = OperationType.CROSS_FS_COPY_DELETE
                        else:
                            shutil.move(str(src), str(dst))
                            op_type = OperationType.DIRECTORY_MOVE

                        rec = ExecutionRecord(
                            id=uuid4(),
                            batch_id=batch_uuid,
                            source_path=str(src),
                            destination_path=str(dst),
                            operation_type=op_type,
                            rollback_state=RollbackState.EXECUTED,
                            executed_at=datetime.now(timezone.utc),
                        )
                        executed.append(rec)
                    else:
                        intent = MoveIntent(
                            file_id=uuid4(),
                            source_path=str(src),
                            destination_path=str(dst),
                            source_sha256="",
                            operation_type=OperationType.LOCAL_MOVE,
                        )
                        rec = AtomicExecutionRunner.execute_move(intent, batch_uuid)
                        executed.append(rec)

            except Exception as e:
                logger.error("Failed to execute tree-diff node %s -> %s: %s", node.source_path, node.target_path, e)
                errors.append({"source": node.source_path, "error": str(e)})

        self._execution_history[batch_uuid] = executed
        return {
            "ok": True,
            "batch_id": str(batch_uuid),
            "executed_count": len(executed),
            "failed_count": len(errors),
            "errors": errors,
        }

    def _execute_remote_node(
        self,
        node: TreeDiffNode,
        batch_uuid: UUID,
    ) -> Optional[ExecutionRecord]:
        """Executes a move, archive or clean operation remotely via SSH."""
        from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import SSHNodeInspector
        inspector = SSHNodeInspector()
        node_id = self._current_node_id
        src = node.source_path
        DiskCleaningPolicy.assert_cleanup_safe(src)

        if node.action == "CLEAN_TEMP":
            py_code = (
                "import os, shutil, sys, time\n"
                "from pathlib import Path\n"
                f"src = Path('{src}')\n"
                "if not src.exists(): sys.exit(2)\n"
                "trash_dir = src.parent / '.hermes_trash'\n"
                "trash_dir.mkdir(parents=True, exist_ok=True)\n"
                "dst = trash_dir / src.name\n"
                "if dst.exists(): dst = trash_dir / f'{src.stem}_{int(time.time())}{src.suffix}'\n"
                "shutil.move(str(src), str(dst))\n"
                "print(str(dst))\n"
            )
            success, out, _ = inspector.execute_remote(node_id, f"python3 -c {subprocess.list2cmdline([py_code])}")
            if not success or "Traceback" in out:
                raise RuntimeError(f"Remote trash failed on {node_id}: {out}")
            lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
            trash_dst = lines[-1] if lines else f"trash://{Path(src).name}"
            return ExecutionRecord(
                id=uuid4(),
                batch_id=batch_uuid,
                source_path=src,
                destination_path=trash_dst,
                operation_type=OperationType.TRASH_DELETE,
                rollback_state=RollbackState.EXECUTED,
                executed_at=datetime.now(timezone.utc),
            )

        elif node.action in ("MOVE", "ARCHIVE"):
            dst = node.target_path
            if not dst:
                return None
            DiskCleaningPolicy.assert_cleanup_safe(dst)
            py_code = (
                "import os, shutil, sys\n"
                "from pathlib import Path\n"
                f"src = Path('{src}')\n"
                f"dst = Path('{dst}')\n"
                "if not src.exists(): sys.exit(2)\n"
                "dst.parent.mkdir(parents=True, exist_ok=True)\n"
                "shutil.move(str(src), str(dst))\n"
                "print('OK')\n"
            )
            success, out, _ = inspector.execute_remote(node_id, f"python3 -c {subprocess.list2cmdline([py_code])}")
            if not success or "OK" not in out:
                raise RuntimeError(f"Remote move failed on {node_id}: {out}")
            return ExecutionRecord(
                id=uuid4(),
                batch_id=batch_uuid,
                source_path=src,
                destination_path=dst,
                operation_type=OperationType.DIRECTORY_MOVE,
                rollback_state=RollbackState.EXECUTED,
                executed_at=datetime.now(timezone.utc),
            )

        return None

    def rollback_batch(self, batch_id: UUID | str) -> Dict[str, Any]:
        """
        Reverses executed operations from batch_id in LIFO order.
        """
        uuid_val = UUID(str(batch_id))
        if uuid_val not in self._execution_history:
            return {"ok": False, "batch_id": str(batch_id), "message": "Batch not found"}

        records = self._execution_history[uuid_val]
        if not records:
            return {"ok": True, "batch_id": str(batch_id), "reverted_count": 0, "failed_count": 0, "message": "No actions to rollback"}

        reverted_count = 0
        failed_count = 0
        is_remote = self._current_node_id not in ("laptop", "local", "localhost")

        for rec in reversed(records):
            if rec.rollback_state != RollbackState.EXECUTED:
                continue

            if is_remote:
                from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import SSHNodeInspector
                inspector = SSHNodeInspector()
                py_code = (
                    "import shutil, sys\n"
                    "from pathlib import Path\n"
                    f"dst = Path('{rec.destination_path}')\n"
                    f"src = Path('{rec.source_path}')\n"
                    "if not dst.exists(): sys.exit(2)\n"
                    "src.parent.mkdir(parents=True, exist_ok=True)\n"
                    "shutil.move(str(dst), str(src))\n"
                    "print('ROLLBACK_OK')\n"
                )
                success, out, _ = inspector.execute_remote(self._current_node_id, f"python3 -c {subprocess.list2cmdline([py_code])}")
                if success and "ROLLBACK_OK" in out:
                    reverted_count += 1
                else:
                    failed_count += 1
                continue

            if rec.operation_type in (
                OperationType.LOCAL_MOVE,
                OperationType.CROSS_FS_COPY_DELETE,
                OperationType.DIRECTORY_MOVE,
            ):
                dst = Path(rec.destination_path)
                src = Path(rec.source_path)
                if not dst.exists():
                    failed_count += 1
                    continue
                try:
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dst), str(src))
                    reverted_count += 1
                except Exception as exc:
                    logger.error("Rollback failed for %s -> %s: %s", dst, src, exc)
                    failed_count += 1

        return {
            "ok": True,
            "batch_id": str(batch_id),
            "reverted_count": reverted_count,
            "failed_count": failed_count,
        }


# Singleton service instance
subtree_profiler_service = SubtreeProfilerService()
