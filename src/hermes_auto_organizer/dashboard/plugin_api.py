"""
Hermes Auto-Organizer Dashboard Plugin API.

Mounted at /api/plugins/auto-organizer/ by the Hermes dashboard plugin loader.
Connects to PostgreSQL 16 (shared-pg) to expose monitored roots, detected anomalies,
modular rule synthesis matrices, dry-run previews, and atomic reorganization execution.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

# Ensure local package is in sys.path when loaded in external environments or containers
_this_file = Path(__file__).resolve()
for _candidate in [_this_file.parent, _this_file.parent.parent, _this_file.parents[2]]:
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import asyncpg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from hermes_auto_organizer.domain.models import FileNode
from hermes_auto_organizer.domain.rule_engine import (
    evaluate_modular_rule,
    resolve_destination_path,
)
from hermes_auto_organizer.infrastructure.storage.docker_mounts import docker_mount_service

router = APIRouter()
logger = logging.getLogger("hermes.plugins.auto_organizer")

DB_HOST = os.getenv("HERMES_DB_HOST", "localhost")
DB_PORT = int(os.getenv("HERMES_DB_PORT", "5433"))
DB_USER = os.getenv("HERMES_DB_USER", "pgadmin")
DB_PASS = os.getenv("HERMES_DB_PASSWORD", "81914287fd58ccba48967c0b8483dfc74cced7f28c14d196")
DB_NAME = os.getenv("HERMES_DB_NAME", "agent_memory")

DSN = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# In-memory session store for pending dry-runs
_DRY_RUN_CACHE: Dict[str, Dict[str, Any]] = {}


async def _get_connection() -> Optional[asyncpg.Connection]:
    try:
        conn = await asyncio.wait_for(asyncpg.connect(DSN), timeout=2.5)
        return conn
    except Exception as exc:
        logger.warning("Failed to connect to PostgreSQL %s: %s", DSN, exc)
        return None


# Request / Response Schemas
class RuleToggleRequest(BaseModel):
    rule_id: str
    active: bool


class ModularRuleCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    match_mode: str = "all"  # "all" (AND) or "any" (OR)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    target_path_template: str
    priority: int = 10
    state: str = "USER_APPROVED"


class RuleTestRequest(BaseModel):
    match_mode: str = "all"
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    target_path_template: str = "/media/privat-buero/Archiv/{year}/"
    max_items: int = 20


class DryRunRequest(BaseModel):
    rule_ids: Optional[List[str]] = None
    max_items: int = 50


class ExecuteRequest(BaseModel):
    dry_run_batch_id: str


class RollbackRequest(BaseModel):
    batch_id: str


class PathCheckRequest(BaseModel):
    path: str


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check verifying database connectivity."""
    conn = await _get_connection()
    db_ok = False
    table_count = 0
    if conn:
        try:
            row = await conn.fetchrow(
                """
                SELECT count(*) as c FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND (table_name LIKE 'file_%' OR table_name LIKE 'storage_%' OR table_name LIKE 'organization_%');
                """
            )
            table_count = int(row["c"]) if row else 0
            db_ok = True
        except Exception:
            pass
        finally:
            await conn.close()

    return {
        "ok": True,
        "plugin": "auto-organizer",
        "version": "0.2.0",
        "database_connected": db_ok,
        "table_count": table_count,
        "timestamp": time.time(),
    }


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Summary metrics of roots, indexed files, anomalies, and active rules."""
    conn = await _get_connection()
    if not conn:
        return {
            "total_files": 0,
            "total_size_mb": 0.0,
            "total_roots": 0,
            "open_anomalies": 0,
            "active_rules": 0,
            "recent_batches": 0,
            "db_connected": False,
        }

    try:
        f_row = await conn.fetchrow("SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as size FROM file_nodes WHERE NOT is_deleted;")
        r_row = await conn.fetchrow("SELECT COUNT(*) as count FROM storage_roots WHERE is_active;")
        a_row = await conn.fetchrow("SELECT COUNT(*) as count FROM structural_anomalies WHERE status = 'open';")
        rule_row = await conn.fetchrow("SELECT COUNT(*) as count FROM organization_rules WHERE state = 'USER_APPROVED';")
        b_row = await conn.fetchrow("SELECT COUNT(DISTINCT batch_id) as count FROM execution_log;")

        return {
            "total_files": int(f_row["count"] or 0),
            "total_size_mb": round(float(f_row["size"] or 0) / (1024 * 1024), 2),
            "total_roots": int(r_row["count"] or 0),
            "open_anomalies": int(a_row["count"] or 0),
            "active_rules": int(rule_row["count"] or 0),
            "recent_batches": int(b_row["count"] or 0),
            "db_connected": True,
        }
    finally:
        await conn.close()


@router.get("/mounts")
async def list_mounts() -> Dict[str, Any]:
    """
    Return all discovered Docker container mounts, host-container mappings,
    read/write permissions, and disk space usage.
    """
    mounts = docker_mount_service.get_mounts(force_refresh=True)
    writable_count = sum(1 for m in mounts if m.get("is_writable"))
    total_free_gb = round(sum(m.get("free_gb", 0) for m in mounts if m.get("is_writable")), 1)
    
    return {
        "ok": True,
        "in_container": docker_mount_service.is_in_container(),
        "total_mounts": len(mounts),
        "writable_mounts": writable_count,
        "total_free_gb": total_free_gb,
        "mounts": mounts,
    }


@router.post("/mounts/check")
async def check_mount_path(req: PathCheckRequest) -> Dict[str, Any]:
    """
    Validate whether an arbitrary path (Host or Container) is within
    accessible and writable container mounts.
    """
    return docker_mount_service.validate_destination_path(req.path)


@router.get("/roots")
async def list_roots() -> List[Dict[str, Any]]:
    """Return all registered storage roots with their file count and size."""
    conn = await _get_connection()
    if not conn:
        return []

    try:
        rows = await conn.fetch(
            """
            SELECT r.id, r.root_name, r.root_type, r.uri_path, r.watch_mode, r.is_active,
                   COUNT(f.id) as file_count,
                   COALESCE(SUM(f.size_bytes), 0) as total_size
            FROM storage_roots r
            LEFT JOIN file_nodes f ON f.root_id = r.id AND NOT f.is_deleted
            GROUP BY r.id, r.root_name, r.root_type, r.uri_path, r.watch_mode, r.is_active
            ORDER BY r.root_name ASC;
            """
        )
        return [
            {
                "id": str(r["id"]),
                "name": r["root_name"],
                "type": r["root_type"],
                "uri_path": r["uri_path"],
                "watch_mode": r["watch_mode"],
                "is_active": r["is_active"],
                "file_count": int(r["file_count"]),
                "size_mb": round(float(r["total_size"]) / (1024 * 1024), 2),
            }
            for r in rows
        ]
    finally:
        await conn.close()


@router.get("/anomalies")
async def list_anomalies(status: str = "open", limit: int = 50) -> List[Dict[str, Any]]:
    """Return open anomalies (dump zone files, duplicates, unclassified items)."""
    conn = await _get_connection()
    if not conn:
        return []

    try:
        rows = await conn.fetch(
            """
            SELECT a.id, a.file_id, a.anomaly_type, a.status, a.confidence,
                   a.explanation, a.recommended_action, a.created_at,
                   f.file_name, f.physical_path, f.size_bytes, f.relative_path
            FROM structural_anomalies a
            JOIN file_nodes f ON f.id = a.file_id
            WHERE a.status = $1
            ORDER BY a.created_at DESC
            LIMIT $2;
            """,
            status,
            limit,
        )
        return [
            {
                "id": str(r["id"]),
                "file_id": str(r["file_id"]),
                "file_name": r["file_name"],
                "relative_path": r["relative_path"],
                "physical_path": r["physical_path"],
                "size_kb": round(r["size_bytes"] / 1024, 1),
                "anomaly_type": r["anomaly_type"],
                "confidence": float(r["confidence"]),
                "suggested_target": r["recommended_action"],
                "explanation": r["explanation"],
                "detected_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    finally:
        await conn.close()


@router.get("/rules")
async def list_rules() -> List[Dict[str, Any]]:
    """Return all organization rules and their modular condition structures."""
    conn = await _get_connection()
    if not conn:
        return []

    try:
        rows = await conn.fetch(
            """
            SELECT id, rule_name, description, source_root_id, target_root_id,
                   source_pattern, condition_json, target_path_template, state,
                   dry_run_last_count, created_at, updated_at
            FROM organization_rules
            ORDER BY created_at ASC;
            """
        )
        result = []
        for r in rows:
            cond_data = r["condition_json"]
            if isinstance(cond_data, str):
                try:
                    cond_data = json.loads(cond_data)
                except Exception:
                    cond_data = {}
            elif cond_data is None:
                cond_data = {}

            result.append({
                "id": str(r["id"]),
                "name": r["rule_name"],
                "description": r["description"] or "",
                "source_root_id": str(r["source_root_id"]) if r["source_root_id"] else None,
                "target_root_id": str(r["target_root_id"]) if r["target_root_id"] else None,
                "source_pattern": r["source_pattern"],
                "condition_json": cond_data,
                "target_template": r["target_path_template"],
                "state": r["state"],
                "dry_run_last_count": r["dry_run_last_count"] or 0,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
        return result
    finally:
        await conn.close()


@router.post("/rules/toggle")
async def toggle_rule(req: RuleToggleRequest) -> Dict[str, Any]:
    """Toggle a rule between USER_APPROVED and DISABLED/STAGED."""
    conn = await _get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    new_state = "USER_APPROVED" if req.active else "DISABLED"
    try:
        rule_uuid = UUID(req.rule_id)
        await conn.execute(
            "UPDATE organization_rules SET state = $1, updated_at = NOW() WHERE id = $2;",
            new_state,
            rule_uuid,
        )
        return {"ok": True, "rule_id": req.rule_id, "state": new_state}
    finally:
        await conn.close()


@router.post("/rules")
async def create_modular_rule(req: ModularRuleCreateRequest) -> Dict[str, Any]:
    """Create a modular file organization and cleanup rule in PostgreSQL."""
    conn = await _get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        rule_id = uuid4()
        condition_payload = {
            "match_mode": req.match_mode,
            "conditions": req.conditions,
        }
        await conn.execute(
            """
            INSERT INTO organization_rules (
                id, rule_name, description, source_root_id, target_root_id,
                source_pattern, condition_json, target_path_template, state
            ) VALUES ($1, $2, $3, NULL, NULL, '*', $4, $5, $6);
            """,
            rule_id,
            req.name,
            req.description or "Modular rule created from Hermes Dashboard",
            json.dumps(condition_payload),
            req.target_path_template,
            req.state,
        )
        return {"ok": True, "rule_id": str(rule_id), "name": req.name}
    finally:
        await conn.close()


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str) -> Dict[str, Any]:
    """Delete an organization rule by ID."""
    conn = await _get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        r_uuid = UUID(rule_id)
        await conn.execute("DELETE FROM organization_rules WHERE id = $1;", r_uuid)
        return {"ok": True, "rule_id": rule_id}
    finally:
        await conn.close()


@router.post("/rules/test")
async def test_modular_rule(req: RuleTestRequest) -> Dict[str, Any]:
    """
    Live simulation test of a modular rule against indexed files in PostgreSQL.
    Returns matched file count and preview matches without altering disk.
    """
    conn = await _get_connection()
    if not conn:
        return {"ok": False, "error": "Database unavailable", "matches_count": 0, "sample_matches": []}

    try:
        rows = await conn.fetch(
            """
            SELECT f.id, f.root_id, f.relative_path, f.physical_path, f.file_name,
                   f.size_bytes, f.mtime, f.file_extension, f.content_sha256,
                   e.summary_text
            FROM file_nodes f
            LEFT JOIN file_extractions e ON e.content_sha256 = f.content_sha256
            WHERE NOT f.is_deleted
            ORDER BY f.mtime DESC
            LIMIT 500;
            """
        )
        rule_cond = {
            "match_mode": req.match_mode,
            "conditions": req.conditions,
        }

        matched_items = []
        for r in rows:
            node = FileNode(
                id=r["id"],
                root_id=r["root_id"],
                relative_path=r["relative_path"],
                physical_path=r["physical_path"],
                file_name=r["file_name"],
                size_bytes=r["size_bytes"],
                mtime=r["mtime"],
                file_extension=r["file_extension"],
                content_sha256=r["content_sha256"],
            )
            if evaluate_modular_rule(rule_cond, node, extraction_text=r["summary_text"]):
                dest = resolve_destination_path(req.target_path_template, node)
                m_check = docker_mount_service.validate_destination_path(dest)
                matched_items.append({
                    "file_name": node.file_name,
                    "source_path": node.physical_path,
                    "destination_path": dest,
                    "size_kb": round(node.size_bytes / 1024, 1),
                    "mtime": node.mtime.isoformat(),
                    "mount_valid": m_check["valid"],
                    "mount_message": m_check["message"],
                })

        return {
            "ok": True,
            "matches_count": len(matched_items),
            "sample_matches": matched_items[:req.max_items],
        }
    finally:
        await conn.close()


@router.post("/dry-run")
async def dry_run_simulation(req: DryRunRequest) -> Dict[str, Any]:
    """
    Simulate reorganization: compute S_now -> S_ideal based on active modular rules.
    Detects collisions, boundary risks, and validates Docker mount write permissions.
    """
    conn = await _get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    batch_id = f"dry_{uuid4().hex[:12]}"
    try:
        # Fetch active rules
        rules_rows = await conn.fetch("SELECT * FROM organization_rules WHERE state = 'USER_APPROVED';")
        
        # Fetch candidates
        nodes_rows = await conn.fetch(
            """
            SELECT f.id, f.root_id, f.relative_path, f.physical_path, f.file_name,
                   f.size_bytes, f.mtime, f.file_extension, f.content_sha256,
                   e.summary_text
            FROM file_nodes f
            LEFT JOIN file_extractions e ON e.content_sha256 = f.content_sha256
            WHERE NOT f.is_deleted
            ORDER BY f.mtime DESC
            LIMIT 500;
            """
        )

        actions: List[Dict[str, Any]] = []
        seen_destinations: set[str] = set()

        for nr in nodes_rows:
            if len(actions) >= req.max_items:
                break

            node = FileNode(
                id=nr["id"],
                root_id=nr["root_id"],
                relative_path=nr["relative_path"],
                physical_path=nr["physical_path"],
                file_name=nr["file_name"],
                size_bytes=nr["size_bytes"],
                mtime=nr["mtime"],
                file_extension=nr["file_extension"],
                content_sha256=nr["content_sha256"],
            )

            for rr in rules_rows:
                cond_data = rr["condition_json"]
                if isinstance(cond_data, str):
                    try:
                        cond_data = json.loads(cond_data)
                    except Exception:
                        cond_data = {}
                elif cond_data is None:
                    cond_data = {}

                if evaluate_modular_rule(
                    cond_data,
                    node,
                    extraction_text=nr["summary_text"],
                    source_pattern=rr["source_pattern"],
                ):
                    dst = resolve_destination_path(rr["target_path_template"], node)
                    src = node.physical_path

                    # Check container mount validity & writeability
                    m_check = docker_mount_service.validate_destination_path(dst)
                    mount_valid = m_check["valid"]

                    # Check collision
                    has_collision = dst in seen_destinations or os.path.exists(dst)
                    seen_destinations.add(dst)

                    safe_to_execute = (not has_collision) and mount_valid

                    actions.append({
                        "file_id": str(node.id),
                        "file_name": node.file_name,
                        "source_path": src,
                        "destination_path": dst,
                        "size_bytes": node.size_bytes,
                        "operation": "LOCAL_MOVE" if src.split("/")[1:3] == dst.split("/")[1:3] else "CROSS_FS_COPY_DELETE",
                        "collision": has_collision,
                        "mount_valid": mount_valid,
                        "mount_warning": m_check["message"] if not mount_valid else None,
                        "rule_name": rr["rule_name"],
                        "safe_to_execute": safe_to_execute,
                    })
                    break

        result = {
            "batch_id": batch_id,
            "actions_count": len(actions),
            "collisions_count": sum(1 for a in actions if a["collision"]),
            "unmounted_count": sum(1 for a in actions if not a.get("mount_valid", True)),
            "safe_count": sum(1 for a in actions if a["safe_to_execute"]),
            "actions": actions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Cache in memory for execution
        _DRY_RUN_CACHE[batch_id] = result
        return result
    finally:
        await conn.close()


@router.post("/execute")
async def execute_batch(req: ExecuteRequest) -> Dict[str, Any]:
    """Execute dry-run batch actions atomically with rollback recording."""
    batch_data = _DRY_RUN_CACHE.get(req.dry_run_batch_id)
    if not batch_data:
        raise HTTPException(status_code=404, detail="Dry run batch expired or not found")

    actions = batch_data.get("actions", [])
    if not actions:
        return {"ok": True, "executed": 0, "message": "No actions to execute"}

    conn = await _get_connection()
    executed_count = 0
    failed_count = 0
    batch_uuid = uuid4()

    try:
        from send2trash import send2trash
    except ImportError:
        send2trash = None

    for act in actions:
        if not act.get("safe_to_execute"):
            continue

        src = Path(act["source_path"])
        dst = Path(act["destination_path"])
        file_id = UUID(act["file_id"])

        if not src.exists():
            failed_count += 1
            continue

        # Prevent executing moves outside mounted writable container directories
        m_check = docker_mount_service.validate_destination_path(str(dst))
        if not m_check["valid"]:
            logger.warning("Aborting execution of %s -> %s: %s", src, dst, m_check["message"])
            failed_count += 1
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            # Safe copy-verify-trash
            shutil.copy2(src, dst)
            if send2trash:
                send2trash(str(src))
            else:
                trash_dir = src.parent / ".hermes_trash"
                trash_dir.mkdir(exist_ok=True)
                shutil.move(src, trash_dir / src.name)

            executed_count += 1

            if conn:
                await conn.execute(
                    """
                    INSERT INTO execution_log (
                        id, batch_id, rule_id, file_id, source_path, destination_path,
                        source_sha256, operation_type, rollback_state
                    ) VALUES ($1, $2, NULL, $3, $4, $5, 'unknown', $6, 'EXECUTED');
                    """,
                    uuid4(),
                    batch_uuid,
                    file_id,
                    str(src),
                    str(dst),
                    act["operation"],
                )
        except Exception as exc:
            logger.error("Failed to execute relocation %s -> %s: %s", src, dst, exc)
            failed_count += 1

    if conn:
        await conn.close()

    _DRY_RUN_CACHE.pop(req.dry_run_batch_id, None)

    return {
        "ok": True,
        "batch_id": str(batch_uuid),
        "executed_count": executed_count,
        "failed_count": failed_count,
        "rollback_available": executed_count > 0,
    }


@router.post("/rollback")
async def rollback_batch(req: RollbackRequest) -> Dict[str, Any]:
    """Revert an executed reorganization batch by ID."""
    conn = await _get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        batch_uuid = UUID(req.batch_id)
        rows = await conn.fetch(
            """
            SELECT id, source_path, destination_path, rollback_state
            FROM execution_log
            WHERE batch_id = $1 AND rollback_state = 'EXECUTED';
            """,
            batch_uuid,
        )

        if not rows:
            return {"ok": False, "message": "No executed actions found for batch"}

        reverted_count = 0
        for r in rows:
            src = Path(r["source_path"])
            dst = Path(r["destination_path"])

            # Move destination back to source if destination exists
            if dst.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(dst, src)
                reverted_count += 1

            await conn.execute(
                "UPDATE execution_log SET rollback_state = 'REVERTED', reverted_at = NOW() WHERE id = $1;",
                r["id"],
            )

        return {
            "ok": True,
            "batch_id": req.batch_id,
            "reverted_count": reverted_count,
        }
    finally:
        await conn.close()


@router.get("/batches")
async def list_batches() -> List[Dict[str, Any]]:
    """Return recent reorganization batches."""
    conn = await _get_connection()
    if not conn:
        return []

    try:
        rows = await conn.fetch(
            """
            SELECT batch_id, rollback_state,
                   COUNT(*) as file_count,
                   MIN(executed_at) as started_at
            FROM execution_log
            GROUP BY batch_id, rollback_state
            ORDER BY started_at DESC
            LIMIT 20;
            """
        )
        return [
            {
                "batch_id": str(r["batch_id"]),
                "operator": "dashboard-user",
                "state": r["rollback_state"],
                "file_count": int(r["file_count"]),
                "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            }
            for r in rows
        ]
    finally:
        await conn.close()
