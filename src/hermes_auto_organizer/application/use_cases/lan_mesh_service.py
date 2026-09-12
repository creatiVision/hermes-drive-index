"""
LAN Mesh and Root Partition Cleaner Service.
Provides full multi-device LAN topology awareness (laptop, debian1, xiaomi-mobile),
Syncthing folder mappings, and partition root triage.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from hermes_auto_organizer.application.ports.disk_analyzer_port import LanMeshPort
from hermes_auto_organizer.domain.models import (
    ExecutionRecord,
    LanDeviceNode,
    OperationType,
    RollbackState,
)
from hermes_auto_organizer.domain.policies import DiskCleaningPolicy

logger = logging.getLogger("hermes_auto_organizer.use_cases.lan_mesh")


class LanMeshUseCase:
    """Orchestrates network mesh inspection and root partition triage."""

    def __init__(self, mesh_adapter: LanMeshPort) -> None:
        self._adapter = mesh_adapter
        self._execution_history: Dict[UUID, List[ExecutionRecord]] = {}

    def get_mesh_overview(self) -> dict[str, Any]:
        """Returns the full LAN mesh overview across all 3 nodes and Syncthing folders."""
        devices = self._adapter.get_devices()
        folders = self._adapter.get_syncthing_folders()
        triage = self._adapter.get_root_triage()

        return {
            "network_name": "creatiVision AI-LAN",
            "active_hosts": ["laptop", "debian1", "Note14new (xiaomi-mobile)"],
            "devices": devices,
            "syncthing_folders_count": len(folders),
            "syncthing_folders": folders,
            "root_pollution_candidates_count": len(triage),
            "root_pollution_candidates": triage,
        }

    def get_root_triage_plan(self) -> list[dict[str, Any]]:
        """
        Returns categorized cleanup/organization proposals for loose files
        found sitting in the root of partitions.
        """
        return self._adapter.get_root_triage()

    def execute_root_triage(
        self,
        candidate_paths: Optional[list[str]] = None,
        batch_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """
        Executes verified root triage moves safely with transaction journaling.
        """
        batch_uuid = batch_id or uuid4()
        candidates = self._adapter.get_root_triage()
        filter_set = set(candidate_paths) if candidate_paths else None

        executed: list[ExecutionRecord] = []
        errors: list[dict[str, str]] = []

        for cand in candidates:
            src_str = cand.get("source_path", "")
            if filter_set and src_str not in filter_set:
                continue

            src = Path(src_str)
            dest_dir_str = cand.get("suggested_destination", "")
            if not src.exists() or not dest_dir_str:
                continue

            dst = Path(dest_dir_str) / src.name
            if src.resolve() == dst.resolve():
                continue

            try:
                DiskCleaningPolicy.assert_cleanup_safe(str(src))
                DiskCleaningPolicy.assert_cleanup_safe(str(dst.parent))

                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))

                rec = ExecutionRecord(
                    id=uuid4(),
                    batch_id=batch_uuid,
                    source_path=str(src),
                    destination_path=str(dst),
                    operation_type=OperationType.LOCAL_MOVE,
                    rollback_state=RollbackState.EXECUTED,
                    executed_at=datetime.now(timezone.utc),
                )
                executed.append(rec)
            except Exception as exc:
                logger.error("Failed to triage move %s -> %s: %s", src, dst, exc)
                errors.append({"source": str(src), "destination": str(dst), "error": str(exc)})

        self._execution_history[batch_uuid] = executed

        return {
            "ok": True,
            "batch_id": str(batch_uuid),
            "executed_count": len(executed),
            "errors_count": len(errors),
            "errors": errors,
        }

    def rollback_root_triage(self, batch_id: UUID | str) -> dict[str, Any]:
        """
        Rolls back an executed root triage batch in LIFO order.
        """
        try:
            uuid_val = UUID(str(batch_id))
        except ValueError:
            return {"ok": False, "batch_id": str(batch_id), "message": "Invalid UUID format"}

        if uuid_val not in self._execution_history:
            return {"ok": False, "batch_id": str(batch_id), "message": "Batch not found"}

        records = self._execution_history[uuid_val]
        reverted_count = 0
        failed_count = 0

        for rec in reversed(records):
            if rec.rollback_state != RollbackState.EXECUTED:
                continue

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
