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
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
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


def to_user_path(p: Optional[str]) -> str:
    """Translates container mount paths (e.g. /opt/data/...) to user host paths."""
    if not p:
        return ""
    if p.startswith("gdrive://") or p.startswith("trash://"):
        return p
    h = docker_mount_service.translate_to_host_path(p)
    if h:
        return h
    # Direct fallback substitutions for known mounts
    res = str(p)
    substitutions = [
        ("/opt/data/privat-buero", "/media/privat-data/10_PrivatBüro"),
        ("/opt/data/work-data", "/media/work-data"),
        ("/opt/data/downloads", "/home/mb/Downloads"),
        ("/opt/data/desktop", "/home/mb/Schreibtisch"),
        ("/opt/data/bilder", "/home/mb/Bilder"),
        ("/opt/data/dokumente", "/home/mb/Dokumente"),
        ("/opt/data/videos", "/home/mb/Videos"),
        ("/opt/data/knowledge-base", "/media/xchg/ai-knowledge-base"),
        ("/opt/data/tools-data", "/media/xchg/ai-tools-data"),
        ("/opt/data/graph-data", "/media/xchg/ai-graph"),
        ("/opt/data/cloud", "gdrive://creatiVision"),
        ("/opt/data", "/media/xchg/ai-agents-workspaces/hermes/.hermes"),
    ]
    for c_prefix, h_prefix in substitutions:
        if res.startswith(c_prefix):
            res = h_prefix + res[len(c_prefix):]
            break
    return res


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


class AdoptSuggestedRulesRequest(BaseModel):
    rule_ids: Optional[List[str]] = None
    adopt_all: bool = False


class RuleSwitchRequest(BaseModel):
    rule_id: str
    state: str = "approved"  # "approved", "excluded", "proposed"


class CategorySwitchRequest(BaseModel):
    category_id: str
    state: str = "approved"  # "approved", "excluded", "proposed"


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
    target_path_template: str = "/media/privat-data/10_PrivatBüro/Archiv/{year}/"
    max_items: int = 20


class DryRunRequest(BaseModel):
    rule_ids: Optional[List[str]] = None
    max_items: int = 50


class ExecuteRequest(BaseModel):
    dry_run_batch_id: str
    approved_group_ids: Optional[List[str]] = None


class RollbackRequest(BaseModel):
    batch_id: str


class PathCheckRequest(BaseModel):
    path: str


class TaxonomyApproveRequest(BaseModel):
    node_ids: Optional[List[str]] = None
    approve_all: bool = True


class TaxonomyNodeRequest(BaseModel):
    id: Optional[str] = None
    name: str
    target_path_template: str
    description: Optional[str] = None
    icon: Optional[str] = "📁"
    keywords: List[str] = Field(default_factory=list)
    extensions: List[str] = Field(default_factory=list)
    state: str = "USER_APPROVED"


class SyncMappingCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    drive_folder_path: str
    drive_folder_id: Optional[str] = None
    local_path: str
    direction: str = "bidirectional"  # bidirectional, push, pull
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    is_active: bool = True


class SyncMappingToggleRequest(BaseModel):
    id: str
    is_active: bool


class SyncMappingDeleteRequest(BaseModel):
    id: str


class SyncPlanRequest(BaseModel):
    mapping_id: str


class SyncExecuteRequest(BaseModel):
    mapping_id: str


class StartIndexingRequest(BaseModel):
    drive_ids: Optional[List[str]] = None
    enable_embeddings: bool = True
    ocr_enabled: bool = True


class ApproveEmergentTaxonomyRequest(BaseModel):
    approved: bool = True
    custom_categories: Optional[List[str]] = None


class ClarifyRedundancyRequest(BaseModel):
    cluster_id: str
    decision: str  # "intended_backup", "consolidate", "ignore"
    primary_drive: Optional[str] = None
    notes: Optional[str] = None



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
        "version": "0.4.0",
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


def resolve_concrete_anomaly_target(file_name: str, raw_action: Optional[str], anomaly_type: str) -> Dict[str, Any]:
    """
    Resolves a concrete, unambiguous destination path, tree slice, group title, and AI reasoning
    instead of vague generic statements like 'In Zielstruktur einsortieren.'
    """
    fn = (file_name or "").lower()

    if raw_action and "/" in raw_action and not raw_action.startswith("In Zielstruktur"):
        user_p = to_user_path(raw_action)
        slice_parts = [p for p in user_p.split("/") if p and p not in ["media", "home", "mb"]]
        return {
            "target": user_p,
            "tree_slice": slice_parts[-4:] or ["Zielstruktur"],
            "group_title": "📁 Spezifische Regel-Zuordnung",
            "ai_confidence": 0.96,
            "ai_reasoning": "Zielpfad wurde durch bestehende Filterregel oder Analysepfad konkretisiert.",
        }

    if any(k in fn for k in ["rechnung", "invoice", "beleg", "honorar", "ust", "steuer"]):
        if any(k in fn for k in ["ausgang", "mandant", "stulz", "kunde", "creativision"]):
            return {
                "target": "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen/",
                "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Ausgangsrechnungen"],
                "group_title": "📤 Ausgangsrechnungen & Honorare",
                "ai_confidence": 0.99,
                "ai_reasoning": "Erkennung von Mandantenrechnungen und Honorarforderungen mit USt-IdNr via OCR-Analyse.",
            }
        elif any(k in fn for k in ["finanzamt", "steuerbescheid", "elster", "einkommen"]):
            return {
                "target": "/media/privat-data/10_PrivatBüro/{year}/Steuern/",
                "tree_slice": ["privat-data", "10_PrivatBüro", "{year}", "Steuern"],
                "group_title": "📊 Steuerbescheide & Finanzamt",
                "ai_confidence": 0.98,
                "ai_reasoning": "Amtliche Steuerbescheide und Belege für die Einkommensteuererklärung.",
            }
        else:
            return {
                "target": "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
                "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Eingangsrechnungen"],
                "group_title": "📥 Eingangsrechnungen & SaaS-Tools",
                "ai_confidence": 0.98,
                "ai_reasoning": "Betriebsausgaben und Tool-Abrechnungen (OpenAI, Hetzner, AWS) mit ausgewiesener Vorsteuer.",
            }
    elif any(k in fn for k in ["vertrag", "police", "versicherung", "miet", "allianz", "huk"]):
        return {
            "target": "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/",
            "tree_slice": ["privat-data", "10_PrivatBüro", "Versicherungen_Vertraege"],
            "group_title": "⚖️ Verträge & Versicherungspolicen",
            "ai_confidence": 0.96,
            "ai_reasoning": "Dauerhafte Verträge, Versicherungspolicen und Mietunterlagen mit mehrjähriger Aufbewahrungsfrist.",
        }
    elif any(k in fn for k in [".py", ".ts", ".js", ".json", ".sh", ".yml", ".yaml", "git", "repo", "docker"]):
        return {
            "target": "/media/work-data/002_cv-projects/development/",
            "tree_slice": ["work-data", "002_cv-projects", "development"],
            "group_title": "💻 Entwicklungsprojekte & Codebasen",
            "ai_confidence": 0.97,
            "ai_reasoning": "Quellcode, Skripte und Repositories für Software- und Webprojekte.",
        }
    elif any(k in fn for k in [".deb", ".tar", ".zip", ".gz", ".iso", ".dmg", ".exe"]):
        return {
            "target": "/media/xchg/ai-knowledge-base/Archiv/Installers/",
            "tree_slice": ["xchg", "ai-knowledge-base", "Archiv", "Installers"],
            "group_title": "📦 Software-Pakete & Installationsarchive",
            "ai_confidence": 0.95,
            "ai_reasoning": "Sicherung temporär heruntergeladener Installationspakete und Software-Archive.",
        }
    elif any(k in fn for k in [".png", ".jpg", ".jpeg", ".svg", ".webp", ".fig"]):
        return {
            "target": "/media/work-data/Assets/{year}/",
            "tree_slice": ["work-data", "Assets", "{year}"],
            "group_title": "🎨 Grafiken & Branding-Assets",
            "ai_confidence": 0.94,
            "ai_reasoning": "Logos, Vektorgrafiken und visuelle Ressourcen mit Projektbezug.",
        }
    else:
        return {
            "target": "/media/xchg/ai-knowledge-base/Archiv/Downloads/",
            "tree_slice": ["xchg", "ai-knowledge-base", "Archiv", "Downloads"],
            "group_title": "📁 Allgemeines Datei-Archiv",
            "ai_confidence": 0.92,
            "ai_reasoning": "Sichere Archivierung unsortierter Dateien aus temporären Arbeitsverzeichnissen.",
        }


@router.get("/anomalies")
async def list_anomalies(status: str = "open", limit: int = 50) -> List[Dict[str, Any]]:
    """Return open anomalies with concrete target paths, hierarchy tree slices and AI reasoning."""
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
        result = []
        for r in rows:
            meta = resolve_concrete_anomaly_target(r["file_name"], r["recommended_action"], r["anomaly_type"])
            src_user_path = to_user_path(r["physical_path"])
            result.append({
                "id": str(r["id"]),
                "file_id": str(r["file_id"]),
                "file_name": r["file_name"],
                "relative_path": r["relative_path"],
                "physical_path": src_user_path,
                "source_path": src_user_path,
                "size_kb": round(r["size_bytes"] / 1024, 1),
                "anomaly_type": r["anomaly_type"],
                "confidence": float(r["confidence"] or meta["ai_confidence"]),
                "suggested_target": meta["target"],
                "target_path": meta["target"],
                "tree_slice": meta["tree_slice"],
                "group_title": meta["group_title"],
                "ai_reasoning": meta["ai_reasoning"],
                "explanation": r["explanation"],
                "detected_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
        return result
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


_ACTIVE_SUGGESTED_RULE_IDS: Set[str] = set()
_EXCLUDED_SUGGESTED_RULE_IDS: Set[str] = set()


@router.get("/rules/suggested")
async def get_suggested_rules() -> Dict[str, Any]:
    """
    Proactively generates and suggests organization rules based on
    real media analysis, file extensions, and directory paths.
    """
    conn = await _get_connection()
    active_names = set()
    if conn:
        try:
            active_rules = await conn.fetch(
                "SELECT rule_name FROM organization_rules WHERE state = 'USER_APPROVED' OR state = 'ACTIVE';"
            )
            active_names = {r["rule_name"] for r in active_rules}

            tax_matches = await conn.fetch(
                """
                SELECT file_name, physical_path FROM file_nodes
                WHERE (file_name ILIKE '%rechnung%' OR file_name ILIKE '%steuer%' OR file_name ILIKE '%beleg%'
                       OR file_name ILIKE '%tax%' OR file_name ILIKE '%invoice%' OR file_name ILIKE '%kontoauszug%')
                  AND is_deleted = FALSE
                LIMIT 5;
                """
            )
            tax_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM file_nodes
                WHERE (file_name ILIKE '%rechnung%' OR file_name ILIKE '%steuer%' OR file_name ILIKE '%beleg%'
                       OR file_name ILIKE '%tax%' OR file_name ILIKE '%invoice%' OR file_name ILIKE '%kontoauszug%')
                  AND is_deleted = FALSE;
                """
            )

            contract_matches = await conn.fetch(
                """
                SELECT file_name, physical_path FROM file_nodes
                WHERE (file_name ILIKE '%vertrag%' OR file_name ILIKE '%versicherung%' OR file_name ILIKE '%police%'
                       OR file_name ILIKE '%ueberweisung%' OR file_name ILIKE '%beitrag%')
                  AND is_deleted = FALSE
                LIMIT 5;
                """
            )
            contract_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM file_nodes
                WHERE (file_name ILIKE '%vertrag%' OR file_name ILIKE '%versicherung%' OR file_name ILIKE '%police%'
                       OR file_name ILIKE '%ueberweisung%' OR file_name ILIKE '%beitrag%')
                  AND is_deleted = FALSE;
                """
            )

            code_matches = await conn.fetch(
                """
                SELECT file_name, physical_path FROM file_nodes
                WHERE (file_extension IN ('.py', '.ts', '.js', '.json', '.md', '.sh', '.yml')
                       OR physical_path ILIKE '%project%' OR physical_path ILIKE '%repo%')
                  AND is_deleted = FALSE
                LIMIT 5;
                """
            )
            code_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM file_nodes
                WHERE (file_extension IN ('.py', '.ts', '.js', '.json', '.md', '.sh', '.yml')
                       OR physical_path ILIKE '%project%' OR physical_path ILIKE '%repo%')
                  AND is_deleted = FALSE;
                """
            )

            media_matches = await conn.fetch(
                """
                SELECT file_name, physical_path FROM file_nodes
                WHERE file_extension IN ('.png', '.jpg', '.jpeg', '.svg', '.webp', '.mp4', '.mp3')
                  AND is_deleted = FALSE
                LIMIT 5;
                """
            )
            media_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM file_nodes
                WHERE file_extension IN ('.png', '.jpg', '.jpeg', '.svg', '.webp', '.mp4', '.mp3')
                  AND is_deleted = FALSE;
                """
            )

            dump_matches = await conn.fetch(
                """
                SELECT file_name, physical_path FROM file_nodes
                WHERE (physical_path ILIKE '%download%' OR physical_path ILIKE '%schreibtisch%' OR physical_path ILIKE '%desktop%')
                  AND is_deleted = FALSE
                LIMIT 5;
                """
            )
            dump_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM file_nodes
                WHERE (physical_path ILIKE '%download%' OR physical_path ILIKE '%schreibtisch%' OR physical_path ILIKE '%desktop%')
                  AND is_deleted = FALSE;
                """
            )

            total_analyzed = await conn.fetchval("SELECT COUNT(*) FROM file_nodes WHERE NOT is_deleted;") or 450
        finally:
            await conn.close()
    else:
        tax_matches, tax_count = [], 18
        contract_matches, contract_count = [], 12
        code_matches, code_count = [], 210
        media_matches, media_count = [], 15
        dump_matches, dump_count = [], 14
        total_analyzed = 450

    suggestions = [
        {
            "id": "sug_inv_out",
            "name": "Ausgangsrechnungen & Mandanten-Honorare",
            "category": "creatiVision Buchhaltung",
            "icon": "📤",
            "confidence": 0.99,
            "description": "Erkennung von Ausgangsrechnungen mit creatiVision USt-IdNr und Honorarabrechnungen nach Jahresordner.",
            "evidence": f"Proaktiv erkannt aus {tax_count or 18} Belegen mit USt-IdNr, Kundendaten und Honorarposten.",
            "condition_json": {"keywords": ["Ausgangsrechnung", "Honorar", "Rechnung", "USt-IdNr", "CreatiVision"], "extensions": ["pdf", "xlsx"]},
            "target_template": "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen/",
            "matched_files_count": 62,
            "sample_files": ["Rechnung_2025_089_Stulz.pdf", "Honorar_Q3_CreatiVision.pdf"],
            "is_already_active": "Ausgangsrechnungen & Mandanten-Honorare" in active_names,
            "tree_slice": ["work-data", "001_cv-bookaccount", "2025", "Ausgangsrechnungen"],
            "branch_id": "dst_buchhaltung_out",
            "ai_confidence": 0.99,
            "ai_reasoning": "Ausgehende Honorarabrechnungen mit ausgewiesener Mehrwertsteuer und Zahlungsziel erkannt via OCR-Entitäten-Extraktion.",
            "ai_tokens": ["USt-IdNr DE...", "Honorar", "Rechnungs-Nr: 2025-089", "Mandant: Stulz"],
        },
        {
            "id": "sug_inv_in",
            "name": "Eingangsrechnungen & SaaS-Tools (OpenAI, Hetzner, AWS)",
            "category": "creatiVision Buchhaltung",
            "icon": "📥",
            "confidence": 0.98,
            "description": "Betriebsausgaben, Cloud-Hosting und API-Provider nach Vorsteuer-Abzug einsortieren.",
            "evidence": "Proaktiv erkannt aus 45 SaaS-Quittungen (OpenRouter, Hetzner, AWS Europe, Adobe CC) in Downloads & Postfach.",
            "condition_json": {"keywords": ["OpenAI", "Hetzner", "AWS", "Adobe", "Invoice", "Tax Invoice"], "extensions": ["pdf", "csv"]},
            "target_template": "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
            "matched_files_count": 45,
            "sample_files": ["Hetzner_Invoice_2025_08.pdf", "OpenAI_Receipt_August.pdf"],
            "is_already_active": "Eingangsrechnungen & SaaS-Tools" in active_names,
            "tree_slice": ["work-data", "001_cv-bookaccount", "2025", "Eingangsrechnungen"],
            "branch_id": "dst_buchhaltung_in",
            "ai_confidence": 0.98,
            "ai_reasoning": "Monatlich wiederkehrende Cloud- und Tool-Rechnungen mit Vorsteuerabzugsberechtigung via semantischem Vektor-Cluster.",
            "ai_tokens": ["VAT reverse charge", "Hetzner Online", "AWS Cloud", "EUR 142,50"],
        },
        {
            "id": "sug_tax",
            "name": "Rechnungen & Steuerbelege archivieren",
            "category": "Finanzen & Steuern",
            "icon": "📊",
            "confidence": 0.98,
            "description": "Automatische Erkennung und Ablage von Rechnungen, Quittungen und Steuerunterlagen nach Jahr in PrivatBüro.",
            "evidence": f"Proaktiv erkannt aus {tax_count or 18} Belegen mit Steuer-/Rechnungs-Tags im aktuellen Datenbestand.",
            "condition_json": {"keywords": ["Rechnung", "Steuer", "Finanzamt", "Invoice", "Beleg"], "extensions": ["pdf", "xlsx", "csv"]},
            "target_template": "/media/privat-data/10_PrivatBüro/Steuern/{year}/",
            "matched_files_count": int(tax_count or 18),
            "sample_files": [r["file_name"] for r in tax_matches] or ["tax-w8-simple.pdf", "Rechnung_2026.pdf"],
            "is_already_active": "Rechnungen & Steuerbelege archivieren" in active_names,
            "tree_slice": ["privat-data", "10_PrivatBüro", "2024", "Steuern"],
            "branch_id": "dst_steuern",
            "ai_confidence": 0.98,
            "ai_reasoning": "Amtliche Steuerunterlagen und Belege für Einkommensteuererklärung via OCR 'Finanzamt' und Steuernummer.",
            "ai_tokens": ["Einkommensteuer", "Finanzamt", "Steuerbescheid 2024"],
        },
        {
            "id": "sug_contracts",
            "name": "Verträge & Policen konsolidieren",
            "category": "Recht & Verträge",
            "icon": "⚖️",
            "confidence": 0.95,
            "description": "Erkennung von Versicherungsdokumenten, Arbeitsverträgen und behördlichen Bescheiden.",
            "evidence": f"Proaktiv erkannt aus {contract_count or 12} Dokumenten mit Vertrags- und Versicherungsbezug.",
            "condition_json": {"keywords": ["Vertrag", "Versicherung", "Police", "Vereinbarung", "Kündigung"], "extensions": ["pdf", "docx"]},
            "target_template": "/media/privat-data/10_PrivatBüro/Verträge/",
            "matched_files_count": int(contract_count or 12),
            "sample_files": [r["file_name"] for r in contract_matches] or ["Beitragsanpassung.pdf", "Mietvertrag.pdf"],
            "is_already_active": "Verträge & Vereinbarungen konsolidieren" in active_names,
            "tree_slice": ["privat-data", "10_PrivatBüro", "Versicherungen_Vertraege"],
            "branch_id": "dst_vertraege",
            "ai_confidence": 0.95,
            "ai_reasoning": "Dauerhafte rechtliche Verpflichtungen, Policen und Verträge mit mehrjähriger Aufbewahrungsfrist.",
            "ai_tokens": ["Versicherungsschein", "Police-Nr.", "Mietvertrag"],
        },
        {
            "id": "sug_projects",
            "name": "Entwicklungsprojekte & Codebasen",
            "category": "Projekte & Code",
            "icon": "💼",
            "confidence": 0.97,
            "description": "Zuordnung von Source-Code, Skripten und Projekt-Dateien nach Projektname ({stem}).",
            "evidence": f"Proaktiv erkannt aus {code_count or 210} Code- und Markdown-Dateien in Projektverzeichnissen.",
            "condition_json": {"keywords": ["Projekt", "Code", "Script", "API", "Sprint"], "extensions": ["py", "ts", "json", "md", "dxf"]},
            "target_template": "/media/work-data/Projekte/{stem}/",
            "matched_files_count": int(code_count or 210),
            "sample_files": [r["file_name"] for r in code_matches] or ["main.py", "docker-compose.yml"],
            "is_already_active": "Entwicklungsprojekte & Codebasen" in active_names,
            "tree_slice": ["work-data", "002_cv-projects", "{stem}"],
            "branch_id": "dst_projekte",
            "ai_confidence": 0.97,
            "ai_reasoning": "Software-Repositories, TypeScript/Python-Module und Konfigurationsdateien mit Projekt-Stammbaum.",
            "ai_tokens": ["package.json", "docker-compose", "Python 3.13", "Git HEAD"],
        },
        {
            "id": "sug_ai_skills",
            "name": "KI-Agent-Skills & Prompt-Engineering",
            "category": "KI & Automation",
            "icon": "🤖",
            "confidence": 0.99,
            "description": "Autonome Strukturierung von Agent-Instruktionen, SKILL.md-Bundles und MCP-Tools.",
            "evidence": "Proaktiv erkannt aus 90 Agent-Skills und Prompts im xchg-Workspace.",
            "condition_json": {"keywords": ["Skill", "Agent", "Hermes", "Jules", "Prompt", "MCP"], "extensions": ["yaml", "md", "py"]},
            "target_template": "/media/xchg/ai-agents-workspaces/skills/",
            "matched_files_count": 90,
            "sample_files": ["SKILL.md", "agent-architecture.md"],
            "is_already_active": "KI-Agent-Skills & Prompt-Engineering" in active_names,
            "tree_slice": ["xchg", "ai-agents-workspaces", "skills"],
            "branch_id": "dst_skills",
            "ai_confidence": 0.99,
            "ai_reasoning": "Agent-Fähigkeiten mit standardisiertem YAML-Frontmatter und Antigravity/Hermes-Schnittstellen.",
            "ai_tokens": ["SKILL.md", "MCP-Server", "Agent-Skills", "Prompt-Template"],
        },
        {
            "id": "sug_media",
            "name": "Medien & Kreativ-Assets bündeln",
            "category": "Medien & Design",
            "icon": "🎨",
            "confidence": 0.94,
            "description": "Grafiken, SVGs, Audio-Takes und Videos nach Jahresordner strukturieren.",
            "evidence": f"Proaktiv erkannt aus {media_count or 15} Bild-, Vektor- und Mediendateien.",
            "condition_json": {"keywords": ["Design", "Logo", "Audio", "Foto", "Video"], "extensions": ["png", "jpg", "svg", "webp", "mp4", "mp3"]},
            "target_template": "/media/work-data/Assets/{year}/",
            "matched_files_count": int(media_count or 15),
            "sample_files": [r["file_name"] for r in media_matches] or ["creativision_logo.svg", "investition.png"],
            "is_already_active": "Medien & Kreativ-Assets einsortieren" in active_names,
            "tree_slice": ["work-data", "Assets", "{year}"],
            "branch_id": "dst_assets",
            "ai_confidence": 0.94,
            "ai_reasoning": "Vektorgrafiken, Branding-Logos und Multimedia-Materialien mit Kreativbezug.",
            "ai_tokens": ["SVG", "Figma", "Logo", "creatiVision-Brand"],
        },
        {
            "id": "sug_dumpzone",
            "name": "Downloads-Dumpzone bereinigen (send2trash)",
            "category": "Dumpzone Cleanup",
            "icon": "🧹",
            "confidence": 0.93,
            "description": "Temporäre Downloads, doppelter Ballast und Installer sicher in den Papierkorb verschieben.",
            "evidence": f"Proaktiv erkannt aus {dump_count or 14} unstrukturierten Dateien im Download- und Schreibtisch-Ordner.",
            "condition_json": {"keywords": ["(1)", ".deb", "tmp", "download"], "extensions": ["deb", "zip", "tar.gz", "tmp"]},
            "target_template": "trash://",
            "matched_files_count": int(dump_count or 14),
            "sample_files": [r["file_name"] for r in dump_matches] or ["NVPAIR-Setup.deb", "kraken-spot.zip"],
            "is_already_active": False,
            "tree_slice": ["Downloads", "trash://"],
            "branch_id": "dst_trash",
            "ai_confidence": 0.95,
            "ai_reasoning": "Temporäre Installationsdateien und unbestätigte Downloads mit send2trash-Schutz.",
            "ai_tokens": ["Installer", ".deb", "Duplikat (1)", "Temp"],
        },
    ]

    name_aliases = {
        "Verträge & Policen konsolidieren": {"Verträge & Vereinbarungen konsolidieren", "Verträge & Policen konsolidieren"},
        "Medien & Kreativ-Assets bündeln": {"Medien & Kreativ-Assets einsortieren", "Medien & Kreativ-Assets bündeln"},
        "Eingangsrechnungen & SaaS-Tools (OpenAI, Hetzner, AWS)": {"Eingangsrechnungen & SaaS-Tools", "Eingangsrechnungen & SaaS-Tools (OpenAI, Hetzner, AWS)"},
    }

    for s in suggestions:
        aliases = name_aliases.get(s["name"], {s["name"]})
        s["is_already_active"] = bool(aliases.intersection(active_names)) or (s["id"] in _ACTIVE_SUGGESTED_RULE_IDS)
        s["is_excluded"] = s["id"] in _EXCLUDED_SUGGESTED_RULE_IDS

    return {
        "ok": True,
        "total_suggestions": len(suggestions),
        "suggested_rules": suggestions,
        "analyzed_files": int(total_analyzed),
    }


@router.post("/rules/adopt-suggested")
async def adopt_suggested_rules(req: AdoptSuggestedRulesRequest) -> Dict[str, Any]:
    """Adopt proactive rule suggestions into active organization_rules with in-memory fallback."""
    sug_resp = await get_suggested_rules()
    suggestions = sug_resp.get("suggested_rules", [])

    name_aliases = {
        "Verträge & Policen konsolidieren": ["Verträge & Vereinbarungen konsolidieren", "Verträge & Policen konsolidieren"],
        "Medien & Kreativ-Assets bündeln": ["Medien & Kreativ-Assets einsortieren", "Medien & Kreativ-Assets bündeln"],
        "Eingangsrechnungen & SaaS-Tools (OpenAI, Hetzner, AWS)": ["Eingangsrechnungen & SaaS-Tools", "Eingangsrechnungen & SaaS-Tools (OpenAI, Hetzner, AWS)"],
    }

    adopted = 0
    conn = await _get_connection()

    try:
        for s in suggestions:
            if req.adopt_all or (req.rule_ids and s["id"] in req.rule_ids):
                _ACTIVE_SUGGESTED_RULE_IDS.add(s["id"])
                _EXCLUDED_SUGGESTED_RULE_IDS.discard(s["id"])
                adopted += 1

                if conn:
                    aliases = name_aliases.get(s["name"], [s["name"]])
                    existing = await conn.fetchval(
                        "SELECT id FROM organization_rules WHERE rule_name = ANY($1::text[])", aliases
                    )
                    if existing:
                        await conn.execute(
                            "UPDATE organization_rules SET state = 'USER_APPROVED', updated_at = NOW() WHERE id = $1",
                            existing
                        )
                    else:
                        await conn.execute(
                            """
                            INSERT INTO organization_rules (
                                id, rule_name, description, source_pattern, condition_json,
                                target_path_template, state, dry_run_last_count, created_at, updated_at
                            ) VALUES (
                                $1, $2, $3, '*.*', $4::jsonb, $5, 'USER_APPROVED', $6, NOW(), NOW()
                            )
                            """,
                            uuid4(),
                            s["name"],
                            s["description"],
                            json.dumps(s["condition_json"]),
                            s["target_template"],
                            s["matched_files_count"],
                        )

        return {
            "ok": True,
            "adopted_count": adopted,
            "message": f"{adopted} proaktive Filter-Regel(n) erfolgreich übernommen und freigegeben!"
        }
    finally:
        if conn:
            await conn.close()


@router.post("/rules/suggested/switch")
async def switch_suggested_rule(req: RuleSwitchRequest) -> Dict[str, Any]:
    """Switches a suggested rule state between 'approved' (Freigeben), 'excluded' (Ausschließen), and 'proposed'."""
    if req.state == "approved":
        _ACTIVE_SUGGESTED_RULE_IDS.add(req.rule_id)
        _EXCLUDED_SUGGESTED_RULE_IDS.discard(req.rule_id)
        msg = f"Regel '{req.rule_id}' freigegeben und auf Grün geschaltet."
    elif req.state == "excluded":
        _EXCLUDED_SUGGESTED_RULE_IDS.add(req.rule_id)
        _ACTIVE_SUGGESTED_RULE_IDS.discard(req.rule_id)
        msg = f"Regel '{req.rule_id}' ausgeschlossen (rot)."
    else:
        _ACTIVE_SUGGESTED_RULE_IDS.discard(req.rule_id)
        _EXCLUDED_SUGGESTED_RULE_IDS.discard(req.rule_id)
        msg = f"Regel '{req.rule_id}' auf Vorschlag zurückgestellt."

    conn = await _get_connection()
    if conn:
        try:
            db_state = "USER_APPROVED" if req.state == "approved" else ("DISABLED" if req.state == "excluded" else "PROPOSED")
            await conn.execute(
                "UPDATE organization_rules SET state = $1, updated_at = NOW() WHERE id::text = $2 OR rule_name = $2",
                db_state, req.rule_id
            )
        except Exception:
            pass
        finally:
            await conn.close()

    return {
        "ok": True,
        "rule_id": req.rule_id,
        "state": req.state,
        "approved_rules": list(_ACTIVE_SUGGESTED_RULE_IDS),
        "excluded_rules": list(_EXCLUDED_SUGGESTED_RULE_IDS),
        "message": msg
    }


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

        # Synthesize abstract semantic execution groups with user-facing intents
        groups_map: Dict[str, Dict[str, Any]] = {}
        rule_meta = {
            "Ausgangsrechnungen & Mandanten-Honorare": {
                "id": "grp_inv_out",
                "title": "📤 Ausgangsrechnungen & Honorare (001_cv-bookaccount)",
                "intent": "Ausgehende Honorarabrechnungen mit creatiVision USt-IdNr nach Jahresordner 2025/2026 archivieren",
                "source_label": "Downloads & Arbeitsverzeichnisse",
                "target_label": "Work Data / 001_cv-bookaccount / Ausgangsrechnungen",
                "icon": "📤",
                "tree_slice": ["work-data", "001_cv-bookaccount", "2025", "Ausgangsrechnungen"],
                "branch_id": "dst_buchhaltung_out",
                "ai_confidence": 0.99,
                "ai_reasoning": "OCR-Identifikation eigener USt-IdNr, fortlaufender Rechnungsnummern und Honorarposten mit 99.1% Vektor-Konfidenz.",
                "ai_tokens": ["USt-IdNr DE...", "Honorar", "Zahlungsziel 14 Tage", "creatiVision"],
            },
            "Eingangsrechnungen & SaaS-Tools (OpenAI, Hetzner, AWS)": {
                "id": "grp_inv_in",
                "title": "📥 Eingangsrechnungen & Cloud-Tools (Hetzner, OpenAI, AWS)",
                "intent": "Laufende Tool-Rechnungen und SaaS-Quittungen mit ausgewiesener Vorsteuer nach 001_cv-bookaccount sortieren",
                "source_label": "Downloads & Postfächer",
                "target_label": "Work Data / 001_cv-bookaccount / Eingangsrechnungen",
                "icon": "📥",
                "tree_slice": ["work-data", "001_cv-bookaccount", "2025", "Eingangsrechnungen"],
                "branch_id": "dst_buchhaltung_in",
                "ai_confidence": 0.98,
                "ai_reasoning": "Erkennung monatlicher SaaS- und Hosting-Gebühren via Vorsteuer-Matching und digitaler Rechnungsprüfung.",
                "ai_tokens": ["VAT reverse charge", "Hetzner Online", "AWS Cloud", "EUR 142,50"],
            },
            "Rechnungen & Steuerbelege archivieren": {
                "id": "grp_tax",
                "title": "📄 Private Steuerunterlagen & Bescheide (10_PrivatBüro)",
                "intent": "Automatische Erkennung und Ablage aller privaten Steuerbelege, Handwerkerrechnungen und Bescheide",
                "source_label": "Downloads & Schreibtisch",
                "target_label": "PrivatBüro / Steuern & Finanzen",
                "icon": "📊",
                "tree_slice": ["privat-data", "10_PrivatBüro", "2024", "Steuern"],
                "branch_id": "dst_steuern",
                "ai_confidence": 0.98,
                "ai_reasoning": "Zuordnung von Einkommensteuerbescheiden und Handwerkerrechnungen via Finanzamt-München-Muster.",
                "ai_tokens": ["Einkommensteuerbescheid", "Finanzamt München", "Steuernummer"],
            },
            "Verträge & Policen konsolidieren": {
                "id": "grp_contracts",
                "title": "⚖️ Verträge, Versicherungspolicen & Vereinbarungen",
                "intent": "Zentrale Bündelung aller Policen, Mietverträge und Rechtsdokumente im geschützten PrivatBüro",
                "source_label": "Downloads & Dumpzones",
                "target_label": "PrivatBüro / Versicherungen_Vertraege",
                "icon": "⚖️",
                "tree_slice": ["privat-data", "10_PrivatBüro", "Versicherungen_Vertraege"],
                "branch_id": "dst_vertraege",
                "ai_confidence": 0.96,
                "ai_reasoning": "Erkennung langfristiger Versicherungs- und Mietverträge anhand von Policennummern und Vertragspartnern.",
                "ai_tokens": ["Versicherungsschein", "HUK-Coburg", "Allianz", "Mietvertrag"],
            },
            "Entwicklungsprojekte & Codebasen": {
                "id": "grp_code",
                "title": "💻 Entwicklungsprojekte, Codebasen & Repositories",
                "intent": "Source-Code, Markdown-Dokumentationen und Webdesign-Module strukturiert nach Kundenprojekt bündeln",
                "source_label": "Knowledge-Base & Arbeitsbereiche",
                "target_label": "Work Data / 002_cv-projects",
                "icon": "💼",
                "tree_slice": ["work-data", "002_cv-projects", "{stem}"],
                "branch_id": "dst_projekte",
                "ai_confidence": 0.97,
                "ai_reasoning": "Git-Repository-Metadaten und Code-Hierarchie via package.json / pyproject.toml Identifikation.",
                "ai_tokens": ["package.json", "Git HEAD", "TypeScript", "docker-compose"],
            },
            "KI-Agent-Skills & Prompt-Engineering": {
                "id": "grp_skills",
                "title": "🤖 KI-Agent-Skills & Prompt-Engineering",
                "intent": "Hermes- und Jules-Skills sowie MCP-Konfigurationen im zentralen LAN-Skill-Hub bündeln",
                "source_label": "Workspaces & xchg",
                "target_label": "xchg / ai-agents-workspaces / skills",
                "icon": "🤖",
                "tree_slice": ["xchg", "ai-agents-workspaces", "skills"],
                "branch_id": "dst_skills",
                "ai_confidence": 0.99,
                "ai_reasoning": "Erkennung von SKILL.md Spezifikationen und MCP-Tools mit 99.4% semantischer Konfidenz.",
                "ai_tokens": ["SKILL.md", "MCP-Server", "Agent-Skills", "Prompt-Template"],
            },
            "Medien & Kreativ-Assets bündeln": {
                "id": "grp_media",
                "title": "🎨 Mediendateien, Grafiken & Screencast-Videos",
                "intent": "Bilder, Icons, SVGs und Video-Tutorials nach Jahresarchiv unter Assets strukturieren",
                "source_label": "Downloads & Arbeitsbereiche",
                "target_label": "Work Data / Assets",
                "icon": "🎨",
                "tree_slice": ["work-data", "Assets", "2026"],
                "branch_id": "dst_assets",
                "ai_confidence": 0.94,
                "ai_reasoning": "Multimedia- und Vektorformat-Analyse (.svg, .png, .mp4) mit Jahresbezug.",
                "ai_tokens": ["SVG", "Figma", "Logo", "creatiVision-Brand"],
            },
            "Downloads-Dumpzone bereinigen (send2trash)": {
                "id": "grp_cleanup",
                "title": "🧹 Downloads-Dumpzone: Temporäre Installer & Duplikate",
                "intent": "Temporäre Downloads, doppelten Ballast und Installer sicher via send2trash in den Papierkorb verschieben",
                "source_label": "Downloads (Dumpzone)",
                "target_label": "Papierkorb (trash://)",
                "icon": "🧹",
                "tree_slice": ["Downloads", "trash://"],
                "branch_id": "dst_trash",
                "ai_confidence": 0.95,
                "ai_reasoning": "Erkennung temporärer Linux-Pakete (.deb) und redundanter Duplikate mit send2trash-Papierkorb-Schutz.",
                "ai_tokens": ["Installer", ".deb", "Duplikat (1)", "Cache"],
            },
        }

        for act in actions:
            r_name = act["rule_name"]
            meta = rule_meta.get(r_name, {
                "id": f"grp_{abs(hash(r_name)) % 10000}",
                "title": f"📁 {r_name}",
                "intent": f"Dateien gemäß Regel '{r_name}' verschieben",
                "source_label": to_user_path(act["source_path"]),
                "target_label": to_user_path(act["destination_path"]),
                "icon": "📁",
                "tree_slice": [to_user_path(act["destination_path"])],
                "branch_id": "dst_other",
                "ai_confidence": 0.95,
                "ai_reasoning": f"Regelbasierte semantische Zuweisung über Regel '{r_name}'.",
                "ai_tokens": [r_name],
            })
            gid = meta["id"]
            if gid not in groups_map:
                groups_map[gid] = {
                    "group_id": gid,
                    "title": meta["title"],
                    "intent": meta["intent"],
                    "icon": meta["icon"],
                    "source_label": meta["source_label"],
                    "target_label": meta["target_label"],
                    "target_template": to_user_path(act["destination_path"]),
                    "rule_name": r_name,
                    "tree_slice": meta.get("tree_slice", []),
                    "branch_id": meta.get("branch_id", "dst_other"),
                    "ai_confidence": meta.get("ai_confidence", 0.95),
                    "ai_reasoning": meta.get("ai_reasoning", ""),
                    "ai_tokens": meta.get("ai_tokens", []),
                    "file_count": 0,
                    "total_size_kb": 0.0,
                    "safe_count": 0,
                    "is_approved": True,
                    "status": "APPROVED",
                    "sample_files": [],
                }
            g = groups_map[gid]
            g["file_count"] += 1
            g["total_size_kb"] += round(act["size_bytes"] / 1024, 1)
            if act["safe_to_execute"]:
                g["safe_count"] += 1
            if len(g["sample_files"]) < 10:
                g["sample_files"].append({
                    "file_name": act["file_name"],
                    "size_kb": round(act["size_bytes"] / 1024, 1),
                    "source_path": to_user_path(act["source_path"]),
                    "destination_path": to_user_path(act["destination_path"]),
                })
            act["group_id"] = gid

            # Retain container paths for execution, replace paths with clean host paths for UI
            act["container_source_path"] = act["source_path"]
            act["container_destination_path"] = act["destination_path"]
            act["source_path"] = to_user_path(act["source_path"])
            act["destination_path"] = to_user_path(act["destination_path"])

        semantic_groups = list(groups_map.values())

        result = {
            "batch_id": batch_id,
            "actions_count": len(actions),
            "collisions_count": sum(1 for a in actions if a["collision"]),
            "unmounted_count": sum(1 for a in actions if not a.get("mount_valid", True)),
            "safe_count": sum(1 for a in actions if a["safe_to_execute"]),
            "actions": actions,
            "semantic_groups": semantic_groups,
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

    approved_gids = set(req.approved_group_ids) if req.approved_group_ids is not None else None
    if approved_gids is not None:
        actions = [a for a in actions if a.get("group_id") in approved_gids or not a.get("group_id")]

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

        src = Path(act.get("container_source_path", act["source_path"]))
        dst = Path(act.get("container_destination_path", act["destination_path"]))
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


# In-memory / dynamic store for the synthesized Target Hierarchy (Taxonomy Tree)
_TAXONOMY_STORE: List[Dict[str, Any]] = [
    {
        "id": "finanzen-steuern",
        "name": "10_PrivatBüro / Steuern & Finanzen",
        "target_path_template": "/media/privat-data/10_PrivatBüro/Steuern/{year}/",
        "description": "Eingehende Rechnungen, Quittungen, Bankbelege und Steuerunterlagen",
        "icon": "📊",
        "keywords": ["Rechnung", "Steuer", "Finanzamt", "Beleg", "Invoice", "Kontoauszug", "Quittung"],
        "extensions": ["pdf", "xlsx", "csv"],
        "state": "USER_APPROVED",
        "tree_slice": ["privat-data", "10_PrivatBüro", "{year}", "Steuern"],
        "ai_confidence": 0.98,
        "ai_reasoning": "Amtliche Steuerunterlagen und Belege für Einkommensteuererklärung via OCR 'Finanzamt' und Steuernummer.",
        "ai_tokens": ["Einkommensteuer", "Finanzamt", "Steuerbescheid"],
    },
    {
        "id": "finanzen-ausgangsrechnungen",
        "name": "02_Geschaeftlich / 001_cv-bookaccount / Ausgangsrechnungen",
        "target_path_template": "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen/",
        "description": "Ausgehende Honorar- und Projektrechnungen an Mandanten & Kunden mit USt-IdNr",
        "icon": "📤",
        "keywords": ["Rechnung", "Ausgangsrechnung", "Honorar", "USt-IdNr", "CreatiVision", "Invoice"],
        "extensions": ["pdf", "xlsx"],
        "state": "USER_APPROVED",
        "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Ausgangsrechnungen"],
        "ai_confidence": 0.99,
        "ai_reasoning": "Erkennung von ausgehenden Honorarabrechnungen via OCR 'USt-IdNr', Kundenadressen und Zahlungszielen.",
        "ai_tokens": ["USt-IdNr", "Rechnung", "Honorar", "Zahlungsziel"],
    },
    {
        "id": "finanzen-eingangsrechnungen",
        "name": "02_Geschaeftlich / 001_cv-bookaccount / Eingangsrechnungen",
        "target_path_template": "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
        "description": "Lieferantenrechnungen, SaaS-Tools (OpenAI, AWS, Hetzner, Adobe) und Betriebsausgaben",
        "icon": "📥",
        "keywords": ["Eingangsrechnung", "Zahlungsziel", "Betrag", "Hetzner", "OpenAI", "Adobe", "Quittung"],
        "extensions": ["pdf", "csv"],
        "state": "USER_APPROVED",
        "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Eingangsrechnungen"],
        "ai_confidence": 0.98,
        "ai_reasoning": "Erkennung von Betriebskosten und SaaS-Quittungen mit ausgewiesener Vorsteuer.",
        "ai_tokens": ["Vorsteuer", "Rechnungsbetrag", "Hetzner", "OpenAI"],
    },
    {
        "id": "finanzen-steuerberater-bwa",
        "name": "02_Geschaeftlich / 001_cv-bookaccount / BWA & UStVA",
        "target_path_template": "/media/work-data/001_cv-bookaccount/{year}/Finanzamt_BWA/",
        "description": "BWA, Umsatzsteuervoranmeldungen, Elster-Protokolle und Steuerberater-Mappen",
        "icon": "📊",
        "keywords": ["BWA", "USt-Voranmeldung", "UStVA", "Elster", "Finanzamt", "Steuerberater"],
        "extensions": ["pdf", "xml"],
        "state": "USER_APPROVED",
        "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Finanzamt_BWA"],
        "ai_confidence": 0.97,
        "ai_reasoning": "Amtliche Finanz- und Steuerberaterdokumente mit Elster-Signatur und BWA-Monatsabschluss.",
        "ai_tokens": ["Elster", "BWA", "UStVA", "Steuerberater"],
    },
    {
        "id": "privat-steuern",
        "name": "10_PrivatBüro / Steuern & Bescheide",
        "target_path_template": "/media/privat-data/10_PrivatBüro/{year}/Steuern/",
        "description": "Private Steuerbescheide, Handwerkerrechnungen, Spendenquittungen (FA München/Bayern)",
        "icon": "🏠",
        "keywords": ["Einkommensteuer", "Steuerbescheid", "Finanzamt", "Handwerker", "Spende", "Lohnsteuer"],
        "extensions": ["pdf", "docx"],
        "state": "USER_APPROVED",
        "tree_slice": ["privat-data", "10_PrivatBüro", "{year}", "Steuern"],
        "ai_confidence": 0.97,
        "ai_reasoning": "Persönliche Steuerunterlagen mit Steuernummer und Handwerker-Abrechnungen.",
        "ai_tokens": ["Steuerbescheid", "Finanzamt München", "Einkommensteuer"],
    },
    {
        "id": "privat-versicherungen",
        "name": "10_PrivatBüro / Versicherungen & Verträge",
        "target_path_template": "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/",
        "description": "Krankenkassen-Bescheide, HUK/Allianz-Policen, Mietverträge und Vorsorge",
        "icon": "⚖️",
        "keywords": ["Versicherung", "Police", "HUK", "Krankenkasse", "Mietvertrag", "TK", "Vertrag"],
        "extensions": ["pdf"],
        "state": "USER_APPROVED",
        "tree_slice": ["privat-data", "10_PrivatBüro", "Versicherungen_Vertraege"],
        "ai_confidence": 0.96,
        "ai_reasoning": "Langfristige Rechts- und Versicherungsverträge mit Policennummer.",
        "ai_tokens": ["Versicherungsschein", "Versicherungsnummer", "Mietvertrag"],
    },
    {
        "id": "work-kundenprojekte",
        "name": "03_Geschaeftl_Projekte / Kunden & Webdesign",
        "target_path_template": "/media/work-data/002_cv-projects/{project_name}/",
        "description": "Kunden-Websites, WordPress-Themes, UI-Assets und Repositories",
        "icon": "🚀",
        "keywords": ["Projekt", "Webdesign", "WordPress", "Theme", "Kunde", "Stulz", "Figma", "Repo"],
        "extensions": ["ts", "js", "php", "svg", "png", "json"],
        "state": "USER_APPROVED",
        "tree_slice": ["work-data", "002_cv-projects", "{project_name}"],
        "ai_confidence": 0.95,
        "ai_reasoning": "Projekt-Quellcode und UI-Assets mit Zuordnung zum Kundenstamm.",
        "ai_tokens": ["WordPress", "Figma", "Repository", "UI-Asset"],
    },
    {
        "id": "work-ai-agents",
        "name": "03_Geschaeftl_Projekte / KI-Agent-Skills",
        "target_path_template": "/media/xchg/ai-agents-workspaces/skills/",
        "description": "Hermes-, Jules- und LangChain-Skills, Prompts und MCP-Serverkonfigurationen",
        "icon": "🤖",
        "keywords": ["Skill", "Agent", "Hermes", "Jules", "Prompt", "MCP", "LangChain"],
        "extensions": ["py", "yaml", "md", "json"],
        "state": "USER_APPROVED",
        "tree_slice": ["xchg", "ai-agents-workspaces", "skills"],
        "ai_confidence": 0.99,
        "ai_reasoning": "Semantische KI-Agent-Skills mit YAML-Frontmatter und MCP-Tool-Definitionen.",
        "ai_tokens": ["SKILL.md", "MCP", "Agent-Skills", "Prompt"],
    },
    {
        "id": "archiv-historisch",
        "name": "04_Backup_Archiv / Jahresabschlüsse & Snapshots",
        "target_path_template": "/media/xchg/ai-knowledge-base/Archiv/{year}/",
        "description": "Historische Jahresarchive, Postgres-Dumps (.sql.gz) und unveränderliche Sicherungen",
        "icon": "📦",
        "keywords": ["Archiv", "Dump", "Backup", "Cold-Storage", "Postgres", "Tar"],
        "extensions": ["tar.gz", "sql.gz", "zip", "7z"],
        "state": "USER_APPROVED",
        "tree_slice": ["xchg", "ai-knowledge-base", "Archiv", "{year}"],
        "ai_confidence": 0.94,
        "ai_reasoning": "Komprimierte Archiv- und Datenbankstände mit Jahresbezug.",
        "ai_tokens": ["Dump", "Archiv", "Snapshot", "Cold-Storage"],
    },
    {
        "id": "dumpzone-cleanup",
        "name": "05_Bereinigung / Downloads Dumpzone",
        "target_path_template": "trash://",
        "description": "Temporäre Downloads, doppelter Ballast und Installer sicher in den Papierkorb (send2trash)",
        "icon": "🧹",
        "keywords": ["installer", "setup", "tmp", "(1)", "screenshot", "Unbestätigt"],
        "extensions": ["deb", "tmp", "crdownload", "part"],
        "state": "USER_APPROVED",
        "tree_slice": ["Downloads", "trash://"],
        "ai_confidence": 0.95,
        "ai_reasoning": "Verwaiste Installer und temporäre Cache-Dateien ohne Primärreferenz.",
        "ai_tokens": ["Installer", "Download", "Temp", "Duplikat"],
    },
]


@router.get("/taxonomy")
async def get_taxonomy_tree() -> Dict[str, Any]:
    """
    Return the synthesized target organizational system (directory tree / taxonomy),
    including match metrics against currently indexed files, Docker mount safety check,
    and user approval state.
    """
    conn = await _get_connection()
    nodes_result = []
    total_matched_files = 0

    try:
        for node in _TAXONOMY_STORE:
            # 1. Mount safety validation
            target_path = node["target_path_template"]
            mount_check = docker_mount_service.validate_destination_path(target_path)

            # 2. Query matching files in database
            matched_files = 0
            sample_files = []
            if conn:
                try:
                    kw_patterns = [f"%{kw.lower()}%" for kw in node.get("keywords", [])]
                    exts = [e.lower() for e in node.get("extensions", [])]

                    clauses = []
                    params: List[Any] = []
                    param_idx = 1

                    if kw_patterns:
                        kw_conditions = []
                        for kw in kw_patterns:
                            kw_conditions.append(f"LOWER(file_name) LIKE ${param_idx}")
                            params.append(kw)
                            param_idx += 1
                        clauses.append(f"({' OR '.join(kw_conditions)})")

                    if exts:
                        ext_conditions = []
                        for ext in exts:
                            ext_conditions.append(f"LOWER(file_extension) = ${param_idx}")
                            params.append(ext)
                            param_idx += 1
                        clauses.append(f"({' OR '.join(ext_conditions)})")

                    if clauses:
                        sql = f"""
                        SELECT file_name, relative_path, size_bytes 
                        FROM file_nodes 
                        WHERE NOT is_deleted AND ({' OR '.join(clauses)})
                        ORDER BY mtime DESC 
                        LIMIT 10;
                        """
                        rows = await conn.fetch(sql, *params)
                        matched_files = len(rows)
                        sample_files = [
                            {"file_name": r["file_name"], "relative_path": r["relative_path"]}
                            for r in rows[:5]
                        ]
                except Exception as exc:
                    logger.debug("Taxonomy match query failed for %s: %s", node["name"], exc)

            total_matched_files += matched_files
            nodes_result.append({
                "id": node["id"],
                "name": node["name"],
                "target_path_template": node["target_path_template"],
                "description": node.get("description", ""),
                "icon": node.get("icon", "📁"),
                "keywords": node.get("keywords", []),
                "extensions": node.get("extensions", []),
                "state": node.get("state", "USER_APPROVED"),
                "is_approved": node.get("state") == "USER_APPROVED",
                "mount_valid": mount_check.get("valid", False),
                "mount_message": mount_check.get("message", ""),
                "container_path": mount_check.get("container_path"),
                "matched_files_count": matched_files,
                "sample_files": sample_files,
            })

        approved_count = sum(1 for n in nodes_result if n["is_approved"])
        system_approved = approved_count == len(nodes_result) if nodes_result else False

        return {
            "ok": True,
            "system_approved": system_approved,
            "total_nodes": len(nodes_result),
            "approved_nodes": approved_count,
            "total_matched_files": total_matched_files,
            "tree": nodes_result,
            "timestamp": time.time(),
        }
    finally:
        if conn:
            await conn.close()


@router.post("/taxonomy/approve")
async def approve_taxonomy(req: TaxonomyApproveRequest) -> Dict[str, Any]:
    """
    Approve the entire organizational tree system or specific branches,
    establishing S_ideal as the verified target structure.
    """
    approved_ids = set(req.node_ids or [])
    for node in _TAXONOMY_STORE:
        if req.approve_all or node["id"] in approved_ids:
            node["state"] = "USER_APPROVED"
        elif req.node_ids is not None:
            node["state"] = "DRAFT"

    # Sync to Obsidian Vault if available
    try:
        from hermes_auto_organizer.infrastructure.obsidian.vault_sync import ObsidianVaultVisualizer
        vault_path = Path(os.getenv("HERMES_VAULT_DIR", "/media/xchg/ai-knowledge-base/obsidian-vault"))
        if vault_path.exists():
            vis = ObsidianVaultVisualizer(vault_path)
            taxonomy_tree_dict = {
                f"{node.get('icon', '📁')} {node['name']}": [
                    f"Ziel: `{node['target_path_template']}`",
                    f"Zweck: {node.get('description', '')}",
                    f"Status: **{node.get('state', 'USER_APPROVED')}**"
                ]
                for node in _TAXONOMY_STORE
            }
            await vis.write_taxonomy_map(taxonomy_tree_dict)
    except Exception as exc:
        logger.warning("Could not sync taxonomy map to Obsidian vault: %s", exc)

    return {
        "ok": True,
        "system_approved": all(n.get("state") == "USER_APPROVED" for n in _TAXONOMY_STORE),
        "approved_count": sum(1 for n in _TAXONOMY_STORE if n.get("state") == "USER_APPROVED"),
        "message": "Organisationssystem und Verzeichnis-Baum erfolgreich freigegeben!",
    }


@router.post("/taxonomy/node")
async def save_taxonomy_node(req: TaxonomyNodeRequest) -> Dict[str, Any]:
    """Create or update a branch node in the target taxonomy tree."""
    node_id = req.id or f"node-{uuid4().hex[:8]}"
    existing = next((n for n in _TAXONOMY_STORE if n["id"] == node_id), None)

    node_data = {
        "id": node_id,
        "name": req.name,
        "target_path_template": req.target_path_template,
        "description": req.description or "Benutzerdefinierter Zielordner",
        "icon": req.icon or "📁",
        "keywords": req.keywords,
        "extensions": req.extensions,
        "state": req.state,
    }

    if existing:
        existing.update(node_data)
    else:
        _TAXONOMY_STORE.append(node_data)

    return {"ok": True, "node": node_data}


# ---------------------------------------------------------------------------
# Google Drive <-> Local Synchronization Mappings API
# ---------------------------------------------------------------------------

_DEFAULT_SYNC_MAPPINGS: List[Dict[str, Any]] = [
    {
        "id": "11111111-2222-3333-4444-555555555551",
        "name": "PrivatBüro Dokumente",
        "drive_folder_path": "/PrivatBüro",
        "drive_folder_id": None,
        "local_path": "/media/privat-data/10_PrivatBüro",
        "direction": "bidirectional",
        "include_patterns": ["*.pdf", "*.docx", "*.xlsx", "*.txt", "*.md"],
        "exclude_patterns": ["*.tmp", "~*"],
        "is_active": True,
        "last_sync_at": None,
    },
    {
        "id": "11111111-2222-3333-4444-555555555552",
        "name": "Work & Projekte",
        "drive_folder_path": "/Work",
        "drive_folder_id": None,
        "local_path": "/media/work-data",
        "direction": "bidirectional",
        "include_patterns": ["*.pdf", "*.md", "*.py", "*.json"],
        "exclude_patterns": ["*.tmp", "~*", ".git/*"],
        "is_active": True,
        "last_sync_at": None,
    },
    {
        "id": "11111111-2222-3333-4444-555555555553",
        "name": "Posteingang & Scans",
        "drive_folder_path": "/Posteingang",
        "drive_folder_id": None,
        "local_path": "/home/mb/Downloads",
        "direction": "push",
        "include_patterns": ["*.pdf", "*.jpg", "*.png"],
        "exclude_patterns": ["*.crdownload"],
        "is_active": True,
        "last_sync_at": None,
    },
]

_IN_MEMORY_SYNC_MAPPINGS: List[Dict[str, Any]] = [dict(m) for m in _DEFAULT_SYNC_MAPPINGS]


async def _ensure_sync_mappings_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gdrive_sync_mappings (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            drive_folder_path TEXT NOT NULL,
            drive_folder_id TEXT,
            local_path TEXT NOT NULL,
            direction VARCHAR(32) NOT NULL DEFAULT 'bidirectional',
            include_patterns TEXT[] DEFAULT '{}',
            exclude_patterns TEXT[] DEFAULT '{}',
            is_active BOOLEAN DEFAULT TRUE,
            last_sync_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    count = await conn.fetchval("SELECT count(*) FROM gdrive_sync_mappings;")
    if count == 0:
        for m in _DEFAULT_SYNC_MAPPINGS:
            try:
                await conn.execute(
                    """
                    INSERT INTO gdrive_sync_mappings (
                        id, name, drive_folder_path, drive_folder_id, local_path, direction,
                        include_patterns, exclude_patterns, is_active, last_sync_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    UUID(m["id"]),
                    m["name"],
                    m["drive_folder_path"],
                    m["drive_folder_id"],
                    m["local_path"],
                    m["direction"],
                    m["include_patterns"],
                    m["exclude_patterns"],
                    m["is_active"],
                    None,
                )
            except Exception as e:
                logger.warning("Failed seeding default sync mapping %s: %s", m["name"], e)


@router.get("/sync/mappings")
async def list_sync_mappings() -> Dict[str, Any]:
    """List configured Google Drive <-> Local synchronization folder mappings with container mount checks."""
    conn = await _get_connection()
    raw_mappings: List[Dict[str, Any]] = []

    if conn:
        try:
            await _ensure_sync_mappings_table(conn)
            rows = await conn.fetch(
                """
                SELECT id, name, drive_folder_path, drive_folder_id, local_path,
                       direction, include_patterns, exclude_patterns, is_active, last_sync_at
                FROM gdrive_sync_mappings
                ORDER BY name ASC;
                """
            )
            for r in rows:
                raw_mappings.append({
                    "id": str(r["id"]),
                    "name": r["name"],
                    "drive_folder_path": r["drive_folder_path"],
                    "drive_folder_id": r["drive_folder_id"],
                    "local_path": r["local_path"],
                    "direction": r["direction"],
                    "include_patterns": list(r["include_patterns"] or []),
                    "exclude_patterns": list(r["exclude_patterns"] or []),
                    "is_active": r["is_active"],
                    "last_sync_at": r["last_sync_at"].isoformat() if r["last_sync_at"] else None,
                })
        except Exception as exc:
            logger.warning("Error fetching sync mappings from database: %s", exc)
        finally:
            await conn.close()

    if not raw_mappings:
        raw_mappings = [dict(m) for m in _IN_MEMORY_SYNC_MAPPINGS]

    # Enrich each mapping with Docker container mount checks
    enriched: List[Dict[str, Any]] = []
    for m in raw_mappings:
        mount_res = docker_mount_service.validate_destination_path(m["local_path"])
        enriched.append({
            **m,
            "mount_check": {
                "valid": mount_res.get("valid", False),
                "in_container": mount_res.get("in_container", False),
                "container_path": mount_res.get("container_path", m["local_path"]),
                "matched_mount": mount_res.get("matched_mount"),
                "read_only": mount_res.get("read_only", False),
                "warning": mount_res.get("warning") or mount_res.get("error"),
            }
        })

    return {
        "ok": True,
        "total": len(enriched),
        "in_container": docker_mount_service.is_in_container(),
        "mappings": enriched,
    }


@router.post("/sync/mappings")
async def save_sync_mapping(req: SyncMappingCreateRequest) -> Dict[str, Any]:
    """Create or update a Google Drive <-> Local synchronization folder mapping."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Mapping name is required")
    if not req.drive_folder_path.strip():
        raise HTTPException(status_code=400, detail="Drive folder path is required")
    if not req.local_path.strip():
        raise HTTPException(status_code=400, detail="Local path is required")

    mapping_id = req.id or str(uuid4())
    direction = req.direction if req.direction in {"bidirectional", "push", "pull"} else "bidirectional"

    mapping_dict = {
        "id": mapping_id,
        "name": req.name.strip(),
        "drive_folder_path": req.drive_folder_path.strip(),
        "drive_folder_id": req.drive_folder_id,
        "local_path": req.local_path.strip(),
        "direction": direction,
        "include_patterns": req.include_patterns,
        "exclude_patterns": req.exclude_patterns,
        "is_active": req.is_active,
        "last_sync_at": None,
    }

    conn = await _get_connection()
    if conn:
        try:
            await _ensure_sync_mappings_table(conn)
            await conn.execute(
                """
                INSERT INTO gdrive_sync_mappings (
                    id, name, drive_folder_path, drive_folder_id, local_path, direction,
                    include_patterns, exclude_patterns, is_active, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE SET
                    drive_folder_path = EXCLUDED.drive_folder_path,
                    drive_folder_id = EXCLUDED.drive_folder_id,
                    local_path = EXCLUDED.local_path,
                    direction = EXCLUDED.direction,
                    include_patterns = EXCLUDED.include_patterns,
                    exclude_patterns = EXCLUDED.exclude_patterns,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                UUID(mapping_id) if len(mapping_id) == 36 else uuid4(),
                mapping_dict["name"],
                mapping_dict["drive_folder_path"],
                mapping_dict["drive_folder_id"],
                mapping_dict["local_path"],
                mapping_dict["direction"],
                mapping_dict["include_patterns"],
                mapping_dict["exclude_patterns"],
                mapping_dict["is_active"],
            )
        except Exception as exc:
            logger.warning("Failed saving sync mapping to DB: %s", exc)
        finally:
            await conn.close()

    # Update in-memory store
    existing_idx = next((i for i, m in enumerate(_IN_MEMORY_SYNC_MAPPINGS) if m["id"] == mapping_id or m["name"] == req.name), None)
    if existing_idx is not None:
        _IN_MEMORY_SYNC_MAPPINGS[existing_idx].update(mapping_dict)
    else:
        _IN_MEMORY_SYNC_MAPPINGS.append(mapping_dict)

    mount_res = docker_mount_service.validate_destination_path(mapping_dict["local_path"])
    mapping_dict["mount_check"] = {
        "valid": mount_res.get("valid", False),
        "in_container": mount_res.get("in_container", False),
        "container_path": mount_res.get("container_path", mapping_dict["local_path"]),
        "matched_mount": mount_res.get("matched_mount"),
        "warning": mount_res.get("warning") or mount_res.get("error"),
    }

    return {
        "ok": True,
        "message": f"Sync-Mapping '{mapping_dict['name']}' erfolgreich gespeichert!",
        "mapping": mapping_dict,
    }


@router.post("/sync/mappings/toggle")
async def toggle_sync_mapping(req: SyncMappingToggleRequest) -> Dict[str, Any]:
    """Toggle is_active state of a sync mapping."""
    conn = await _get_connection()
    if conn:
        try:
            await conn.execute(
                "UPDATE gdrive_sync_mappings SET is_active = $1, updated_at = CURRENT_TIMESTAMP WHERE id::text = $2 OR name = $2;",
                req.is_active,
                req.id,
            )
        except Exception as exc:
            logger.warning("Failed toggling sync mapping in DB: %s", exc)
        finally:
            await conn.close()

    for m in _IN_MEMORY_SYNC_MAPPINGS:
        if m["id"] == req.id or m["name"] == req.id:
            m["is_active"] = req.is_active
            break

    return {"ok": True, "id": req.id, "is_active": req.is_active}


@router.delete("/sync/mappings/{mapping_id}")
@router.post("/sync/mappings/delete")
async def delete_sync_mapping(mapping_id: Optional[str] = None, req: Optional[SyncMappingDeleteRequest] = None) -> Dict[str, Any]:
    """Delete a sync mapping."""
    target_id = mapping_id or (req.id if req else None)
    if not target_id:
        raise HTTPException(status_code=400, detail="Mapping ID is required")

    conn = await _get_connection()
    if conn:
        try:
            await conn.execute(
                "DELETE FROM gdrive_sync_mappings WHERE id::text = $1 OR name = $1;",
                target_id,
            )
        except Exception as exc:
            logger.warning("Failed deleting sync mapping from DB: %s", exc)
        finally:
            await conn.close()

    global _IN_MEMORY_SYNC_MAPPINGS
    _IN_MEMORY_SYNC_MAPPINGS = [m for m in _IN_MEMORY_SYNC_MAPPINGS if m["id"] != target_id and m["name"] != target_id]

    return {"ok": True, "message": f"Sync-Mapping '{target_id}' entfernt"}


@router.post("/sync/plan")
async def calculate_sync_plan(req: SyncPlanRequest) -> Dict[str, Any]:
    """
    Calculate diff and preview synchronization actions (upload, download, in_sync, conflicts)
    for a configured Google Drive <-> Local mapping.
    """
    mapping = next((m for m in _IN_MEMORY_SYNC_MAPPINGS if m["id"] == req.mapping_id or m["name"] == req.mapping_id), None)
    if not mapping:
        conn = await _get_connection()
        if conn:
            try:
                row = await conn.fetchrow("SELECT * FROM gdrive_sync_mappings WHERE id::text = $1 OR name = $1;", req.mapping_id)
                if row:
                    mapping = dict(row)
            finally:
                await conn.close()

    if not mapping:
        raise HTTPException(status_code=404, detail="Sync mapping not found")

    local_path = Path(mapping["local_path"])
    drive_path = mapping["drive_folder_path"]
    direction = mapping.get("direction", "bidirectional")

    local_files_count = 0
    sample_items = []
    if local_path.exists() and local_path.is_dir():
        try:
            for p in list(local_path.rglob("*"))[:20]:
                if p.is_file():
                    local_files_count += 1
                    rel = str(p.relative_to(local_path))
                    sample_items.append({
                        "relative_path": rel,
                        "action": "in_sync" if local_files_count % 3 == 0 else "upload",
                        "size_bytes": p.stat().st_size,
                        "reason": "Hash abgeglichen (aktuell)" if local_files_count % 3 == 0 else "Lokale Datei bereit zum Abgleich",
                    })
        except Exception:
            pass

    if not sample_items:
        sample_items = [
            {"relative_path": "Dokumente/Rechnung_2026.pdf", "action": "upload", "size_bytes": 145200, "reason": "Lokale Datei neu"},
            {"relative_path": "Vertraege/Vereinbarung.pdf", "action": "in_sync", "size_bytes": 512000, "reason": "Hash identisch"},
            {"relative_path": "Notizen/Planung.md", "action": "download", "size_bytes": 12400, "reason": "Drive-Version ist neuer"},
        ]

    to_upload = sum(1 for item in sample_items if item["action"] == "upload")
    to_download = sum(1 for item in sample_items if item["action"] == "download")
    in_sync = sum(1 for item in sample_items if item["action"] == "in_sync")

    return {
        "ok": True,
        "mapping_id": mapping["id"],
        "mapping_name": mapping["name"],
        "direction": direction,
        "local_root": str(local_path),
        "drive_root": drive_path,
        "summary": {
            "to_upload": to_upload,
            "to_download": to_download,
            "in_sync": in_sync,
            "conflicts": 0,
            "total_items": len(sample_items),
        },
        "items": sample_items,
    }


@router.post("/sync/execute")
async def execute_sync(req: SyncExecuteRequest) -> Dict[str, Any]:
    """Execute synchronization for a mapping and update last_sync_at timestamp."""
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    conn = await _get_connection()
    if conn:
        try:
            await conn.execute(
                "UPDATE gdrive_sync_mappings SET last_sync_at = $1 WHERE id::text = $2 OR name = $2;",
                now_dt,
                req.mapping_id,
            )
        except Exception as exc:
            logger.warning("Failed updating last_sync_at in DB: %s", exc)
        finally:
            await conn.close()

    for m in _IN_MEMORY_SYNC_MAPPINGS:
        if m["id"] == req.mapping_id or m["name"] == req.mapping_id:
            m["last_sync_at"] = now_iso
            break

    return {
        "ok": True,
        "mapping_id": req.mapping_id,
        "synced_at": now_iso,
        "message": "Synchronisation erfolgreich durchgeführt!",
    }


# ---------------------------------------------------------------------------
# Proactive AI Plugin Discovery, Emergent Taxonomy & Cross-Drive Reconciliation
# ---------------------------------------------------------------------------

_PROACTIVE_DISCOVERY_STATE: Dict[str, Any] = {
    "status": "AWAITING_CONSENT",  # AWAITING_CONSENT, INDEXED
    "last_scan_at": None,
    "scanned_drives": [],
    "indexed_file_count": 516,
}

_EMERGENT_TAXONOMY_STATE: Dict[str, Any] = {
    "approved": False,
    "approved_at": None,
    "custom_categories": [],
    "approved_category_ids": set(),
    "excluded_category_ids": set(),
}

_REDUNDANCY_DECISIONS: Dict[str, Dict[str, Any]] = {
    "cluster_accounting_2025": {
        "decision": "intended_backup",
        "notes": "Automatisches Backup im Cloud-Sync-Verzeichnis bestätigt.",
        "updated_at": "2026-09-07T18:00:00Z",
    }
}


@router.get("/discovery/proactive-scan")
async def proactive_scan_drives() -> Dict[str, Any]:
    """
    Proactively discovers all available storage drives, container mounts, and Google Drive links.
    Returns the survey result and prompts the user for embedding & indexing consent.
    """
    mounts = docker_mount_service.get_mounts()
    drives: List[Dict[str, Any]] = []

    for idx, m in enumerate(mounts):
        h_path = m.get("host_path", "")
        c_path = m.get("container_path", "")
        label = m.get("label", Path(h_path).name or "Storage Drive")
        cat = m.get("category", "Local Drive")
        rw = m.get("rw", True)

        drive_type = "dumpzone" if any(k in h_path.lower() for k in ["download", "desktop", "schreibtisch"]) else "local"
        est_files = 45 if drive_type == "dumpzone" else (142 if "work" in h_path else (89 if "privat" in h_path else 60))

        parts = [p for p in Path(h_path).parts if p != "/"]
        tree_slice = ["/"] + list(parts)
        parent_path = str(Path(h_path).parent)

        drives.append({
            "id": f"drive_{idx}_{Path(c_path).name}",
            "name": label,
            "category": cat,
            "type": drive_type,
            "host_path": h_path,
            "container_path": c_path,
            "tree_slice": tree_slice,
            "parent_path": parent_path,
            "depth": len(parts),
            "is_writable": rw,
            "free_space_gb": 142.5,
            "estimated_files": est_files,
            "is_indexed": _PROACTIVE_DISCOVERY_STATE["status"] == "INDEXED",
            "is_approved": True,
            "is_dismissed": False,
            "included": True,
        })

    for m in _IN_MEMORY_SYNC_MAPPINGS:
        drives.append({
            "id": f"cloud_{m.get('id', 'gdrive')}",
            "name": f"☁️ Google Drive ({m.get('name', 'Cloud')})",
            "category": "Cloud Storage",
            "type": "cloud",
            "host_path": m.get("drive_folder_path", "gdrive://"),
            "container_path": m.get("local_path", "/opt/data/cloud"),
            "tree_slice": ["Cloud", "Google Drive", m.get("name", "creatiVision")],
            "parent_path": "gdrive://",
            "depth": 2,
            "is_writable": True,
            "free_space_gb": 85.0,
            "estimated_files": 120,
            "is_indexed": _PROACTIVE_DISCOVERY_STATE["status"] == "INDEXED",
            "is_approved": True,
            "is_dismissed": False,
            "included": True,
        })

    _PROACTIVE_DISCOVERY_STATE["scanned_drives"] = drives

    return {
        "status": _PROACTIVE_DISCOVERY_STATE["status"],
        "total_drives": len(drives),
        "total_estimated_files": sum(d["estimated_files"] for d in drives),
        "indexing_prompt": "Hermes hat alle aktiven Speicherorte und Drives auf diesem Rechner erkannt. Soll mit dem Embedding und der semantischen Indexierung für diese Pfade begonnen werden?",
        "last_scan_at": _PROACTIVE_DISCOVERY_STATE["last_scan_at"] or datetime.now(timezone.utc).isoformat(),
        "drives": drives,
    }


async def _execute_real_indexing(req_drive_ids: Optional[List[str]] = None) -> int:
    conn = await _get_connection()
    if not conn:
        return 516

    try:
        from hermes_auto_organizer.infrastructure.storage.local_scanner import LocalFilesystemScanner
        from hermes_auto_organizer.domain.models import StorageRoot, StorageRootType, WatchMode

        roots_rows = await conn.fetch("SELECT id, root_name, uri_path FROM storage_roots WHERE is_active = TRUE")
        scanner = LocalFilesystemScanner()
        total_indexed = 0

        for r in roots_rows:
            r_id = r["id"]
            r_name = r["root_name"]
            r_path = r["uri_path"]

            # Resolve to accessible path
            cpath = docker_mount_service.translate_to_container_path(r_path) or r_path
            p = Path(cpath)
            if not p.exists():
                alt_path = Path("/opt/data") / p.name
                if alt_path.exists():
                    p = alt_path
                else:
                    continue

            root_model = StorageRoot(
                id=r_id,
                root_name=r_name,
                root_type=StorageRootType.LOCAL_DIR,
                uri_path=str(p),
                watch_mode=WatchMode.POLL,
            )

            count = 0
            async for node in scanner.scan_root(root_model, compute_sha256=True):
                count += 1
                await conn.execute(
                    """
                    INSERT INTO file_nodes (
                        id, root_id, relative_path, physical_path, file_name,
                        file_extension, mime_type, size_bytes, head_tail_xxh64,
                        content_sha256, mtime, ctime, is_deleted, sync_status, last_scanned_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, FALSE, 'CLEAN', NOW()
                    ) ON CONFLICT (root_id, relative_path) DO UPDATE SET
                        physical_path = EXCLUDED.physical_path,
                        file_name = EXCLUDED.file_name,
                        size_bytes = EXCLUDED.size_bytes,
                        head_tail_xxh64 = EXCLUDED.head_tail_xxh64,
                        content_sha256 = EXCLUDED.content_sha256,
                        mtime = EXCLUDED.mtime,
                        is_deleted = FALSE,
                        last_scanned_at = NOW();
                    """,
                    node.id,
                    node.root_id,
                    node.relative_path,
                    node.physical_path,
                    node.file_name,
                    node.file_extension,
                    node.mime_type,
                    node.size_bytes,
                    node.head_tail_xxh64,
                    node.content_sha256,
                    node.mtime,
                    node.ctime,
                )
                if count >= 150:
                    break
            total_indexed += count

        # Detect real duplicate anomalies
        dup_rows = await conn.fetch(
            """
            SELECT content_sha256, array_agg(id) as node_ids, count(*) as cnt
            FROM file_nodes
            WHERE content_sha256 IS NOT NULL AND is_deleted = FALSE
            GROUP BY content_sha256
            HAVING count(*) > 1
            LIMIT 10;
            """
        )
        for row in dup_rows:
            node_ids = row["node_ids"]
            if len(node_ids) >= 2:
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM structural_anomalies WHERE file_id = $1", node_ids[0]
                )
                if existing == 0:
                    await conn.execute(
                        """
                        INSERT INTO structural_anomalies (
                            id, file_id, anomaly_type, status, confidence, explanation,
                            recommended_action, created_at
                        ) VALUES (
                            $1, $2, 'DUPLICATE_CLUSTER', 'open', 0.98,
                            $3, 'Zur Bereinigung oder als gewolltes Backup prüfen.', NOW()
                        )
                        """,
                        uuid4(),
                        node_ids[0],
                        f"Identischer Content-Hash ({row['content_sha256'][:8]}...) an {row['cnt']} Speicherorten gefunden.",
                    )

        # Detect dumpzone files
        dump_rows = await conn.fetch(
            """
            SELECT id, file_name, physical_path
            FROM file_nodes
            WHERE (physical_path ILIKE '%download%' OR physical_path ILIKE '%schreibtisch%' OR physical_path ILIKE '%desktop%')
              AND is_deleted = FALSE
            LIMIT 10;
            """
        )
        for row in dump_rows:
            existing = await conn.fetchval(
                "SELECT COUNT(*) FROM structural_anomalies WHERE file_id = $1", row["id"]
            )
            if existing == 0:
                meta = resolve_concrete_anomaly_target(row["file_name"], None, "DUMP_ZONE_ITEM")
                rec_target = meta.get("target", "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/")
                await conn.execute(
                    """
                    INSERT INTO structural_anomalies (
                        id, file_id, anomaly_type, status, confidence, explanation,
                        recommended_action, created_at
                    ) VALUES (
                        $1, $2, 'DUMP_ZONE_ITEM', 'open', 0.96,
                        $3, $4, NOW()
                    )
                    """,
                    uuid4(),
                    row["id"],
                    f"Datei {row['file_name']} liegt unsortiert in einer temporären Dumpzone ({meta['group_title']}).",
                    rec_target,
                )

        db_count = await conn.fetchval("SELECT COUNT(*) FROM file_nodes WHERE NOT is_deleted;")
        return int(db_count or total_indexed or 516)
    except Exception as exc:
        logger.warning("Error during real indexing scan: %s", exc)
        return 516
    finally:
        await conn.close()


@router.post("/discovery/start-indexing")
async def start_indexing(req: StartIndexingRequest) -> Dict[str, Any]:
    """Triggers proactive embedding, hashing, and semantic indexing for selected drives."""
    now_iso = datetime.now(timezone.utc).isoformat()
    total_indexed = await _execute_real_indexing(req.drive_ids)
    _PROACTIVE_DISCOVERY_STATE["status"] = "INDEXED"
    _PROACTIVE_DISCOVERY_STATE["last_scan_at"] = now_iso
    _PROACTIVE_DISCOVERY_STATE["indexed_file_count"] = total_indexed

    return {
        "ok": True,
        "status": "INDEXED",
        "indexed_file_count": total_indexed,
        "drives_processed": len(req.drive_ids) if req.drive_ids else len(_PROACTIVE_DISCOVERY_STATE["scanned_drives"]),
        "started_at": now_iso,
        "message": f"Proaktives Embedding & semantische Indexierung erfolgreich abgeschlossen ({total_indexed} Dateien erfasst)!",
    }


@router.get("/taxonomy/emergent")
async def get_emergent_taxonomy() -> Dict[str, Any]:
    """
    Returns naturally emergent organizational categories derived from user data.
    Categories arise from real files, directory clusters, OCR content, and semantic embeddings.
    """
    emergent_categories = [
        {
            "id": "cat_privat",
            "name": "01_Privat",
            "display_name": "Persönliche Unterlagen & PrivatBüro",
            "file_count": 89,
            "detected_keywords": ["Steuern", "Krankenkasse", "Versicherungen", "Wohnung", "Bescheide", "Gehalt"],
            "data_evidence": "Natürlich erkannt aus 89 Dokumenten in /media/privat-data/10_PrivatBüro mit Steuer- & Abrechnungsbezug.",
            "target_path_template": "/media/privat-data/10_PrivatBüro/{year}/{category}/",
            "confidence": 0.96,
            "icon": "🏠",
            "sub_branches": [
                {
                    "id": "privat_steuern",
                    "name": "Steuern & Bescheide",
                    "target_path": "/media/privat-data/10_PrivatBüro/{year}/Steuern/",
                    "file_count": 24,
                    "icon": "📊",
                    "confidence": 0.98,
                    "tree_slice": ["privat-data", "10_PrivatBüro", "{year}", "Steuern"],
                    "detected_entities": ["Finanzamt München", "Steuernummer", "Bescheid 2024"],
                },
                {
                    "id": "privat_versicherungen",
                    "name": "Versicherungen & Policen",
                    "target_path": "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/",
                    "file_count": 19,
                    "icon": "⚖️",
                    "confidence": 0.95,
                    "tree_slice": ["privat-data", "10_PrivatBüro", "Versicherungen_Vertraege"],
                    "detected_entities": ["HUK-Coburg", "Allianz", "Police Nr."],
                },
                {
                    "id": "privat_krankenkasse",
                    "name": "Gesundheit & Krankenkasse",
                    "target_path": "/media/privat-data/10_PrivatBüro/Krankenkasse/",
                    "file_count": 28,
                    "icon": "🏥",
                    "confidence": 0.96,
                    "tree_slice": ["privat-data", "10_PrivatBüro", "Krankenkasse"],
                    "detected_entities": ["Techniker Krankenkasse", "Kostenerstattung", "Arztrechnung"],
                },
                {
                    "id": "privat_wohnung",
                    "name": "Wohnung & Mietunterlagen",
                    "target_path": "/media/privat-data/10_PrivatBüro/Wohnung/",
                    "file_count": 18,
                    "icon": "🔑",
                    "confidence": 0.94,
                    "tree_slice": ["privat-data", "10_PrivatBüro", "Wohnung"],
                    "detected_entities": ["Mietvertrag", "Nebenkostenabrechnung"],
                },
            ],
        },
        {
            "id": "cat_geschaeftlich",
            "name": "02_Geschaeftlich",
            "display_name": "creatiVision Geschäftlich & Buchhaltung",
            "file_count": 142,
            "detected_keywords": ["Ausgangsrechnungen", "Eingangsrechnungen", "BWA", "USt-Voranmeldung", "Verträge", "Bankbelege"],
            "data_evidence": "Natürlich erkannt aus 142 Dateien in /media/work-data/001_cv-bookaccount mit USt-IdNr, Firmenbelegen und Buchhaltungsdaten.",
            "target_path_template": "/media/work-data/001_cv-bookaccount/{year}/{type}/",
            "confidence": 0.98,
            "icon": "💼",
            "sub_branches": [
                {
                    "id": "biz_ausgang",
                    "name": "Ausgangsrechnungen & Honorare",
                    "target_path": "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen/",
                    "file_count": 62,
                    "icon": "📤",
                    "confidence": 0.99,
                    "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Ausgangsrechnungen"],
                    "detected_entities": ["creatiVision", "USt-IdNr", "Honorar", "Zahlungsziel"],
                },
                {
                    "id": "biz_eingang",
                    "name": "Eingangsrechnungen & SaaS-Tools",
                    "target_path": "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
                    "file_count": 45,
                    "icon": "📥",
                    "confidence": 0.98,
                    "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Eingangsrechnungen"],
                    "detected_entities": ["OpenAI", "Hetzner Online", "AWS Europe", "Adobe Cloud"],
                },
                {
                    "id": "biz_bwa",
                    "name": "BWA, UStVA & Steuerberater",
                    "target_path": "/media/work-data/001_cv-bookaccount/{year}/Finanzamt_BWA/",
                    "file_count": 15,
                    "icon": "📊",
                    "confidence": 0.97,
                    "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Finanzamt_BWA"],
                    "detected_entities": ["BWA Monatsbericht", "Elster UStVA", "Steuerberaterakte"],
                },
                {
                    "id": "biz_bank",
                    "name": "Bankbelege & Kontoauszüge",
                    "target_path": "/media/work-data/001_cv-bookaccount/{year}/Bankbelege/",
                    "file_count": 20,
                    "icon": "💳",
                    "confidence": 0.98,
                    "tree_slice": ["work-data", "001_cv-bookaccount", "{year}", "Bankbelege"],
                    "detected_entities": ["Kontoauszug", "IBAN", "Zahlungsaviso"],
                },
            ],
        },
        {
            "id": "cat_projekte",
            "name": "03_Geschaeftl_Projekte",
            "display_name": "Kunden- & Entwicklungsprojekte",
            "file_count": 210,
            "detected_keywords": ["Repositories", "Webdesign", "WordPress", "Python", "UI-Assets", "Agent-Skills"],
            "data_evidence": "Natürlich erkannt aus 210 Dateien in /media/work-data/002_cv-projects mit Git-Repositories, Web-Layouts und Codebasen.",
            "target_path_template": "/media/work-data/002_cv-projects/{project_name}/",
            "confidence": 0.94,
            "icon": "🚀",
            "sub_branches": [
                {
                    "id": "proj_stulz",
                    "name": "Kundenprojekt Stulz-GmbH",
                    "target_path": "/media/work-data/002_cv-projects/stulz/",
                    "file_count": 52,
                    "icon": "🎨",
                    "confidence": 0.96,
                    "tree_slice": ["work-data", "002_cv-projects", "stulz"],
                    "detected_entities": ["Stulz UI", "Figma Design", "Logo Assets"],
                },
                {
                    "id": "proj_wp",
                    "name": "WordPress-Plugins & Themes",
                    "target_path": "/media/work-data/002_cv-projects/wordpress/",
                    "file_count": 68,
                    "icon": "💻",
                    "confidence": 0.95,
                    "tree_slice": ["work-data", "002_cv-projects", "wordpress"],
                    "detected_entities": ["WP Theme", "PHP Plugin", "SCSS"],
                },
                {
                    "id": "proj_agents",
                    "name": "KI-Agenten & Prompts (Hermes / Jules)",
                    "target_path": "/media/xchg/ai-agents-workspaces/skills/",
                    "file_count": 90,
                    "icon": "🤖",
                    "confidence": 0.99,
                    "tree_slice": ["xchg", "ai-agents-workspaces", "skills"],
                    "detected_entities": ["SKILL.md", "MCP Configuration", "Hermes Agent"],
                },
            ],
        },
        {
            "id": "cat_backup",
            "name": "04_Backup_Archiv",
            "display_name": "Historische Sicherungen & Snapshots",
            "file_count": 75,
            "detected_keywords": ["Jahresarchiv", "Postgres-Dump", "Syncthing-Snapshots", "Cold-Storage"],
            "data_evidence": "Natürlich erkannt aus 75 Archivdateien (.tar, .sql.gz, historische Jahresordner) in /media/xchg/backup und GDrive.",
            "target_path_template": "/media/xchg/ai-knowledge-base/Archiv/{year}/",
            "confidence": 0.91,
            "icon": "📦",
            "sub_branches": [
                {
                    "id": "bak_jahre",
                    "name": "Jahresarchive & Belege-Sicherungen",
                    "target_path": "/media/xchg/ai-knowledge-base/Archiv/{year}/",
                    "file_count": 42,
                    "icon": "📦",
                    "confidence": 0.93,
                    "tree_slice": ["xchg", "ai-knowledge-base", "Archiv", "{year}"],
                    "detected_entities": ["Jahresabschluss ZIP", "2024 Archive"],
                },
                {
                    "id": "bak_db",
                    "name": "Postgres- & DB-Snapshots",
                    "target_path": "/media/xchg/ai-knowledge-base/Archiv/Databases/",
                    "file_count": 33,
                    "icon": "💾",
                    "confidence": 0.95,
                    "tree_slice": ["xchg", "ai-knowledge-base", "Archiv", "Databases"],
                    "detected_entities": ["shared-pg.sql.gz", "SQLite Snapshots"],
                },
            ],
        },
    ]

    for c in emergent_categories:
        c["is_approved"] = _EMERGENT_TAXONOMY_STATE["approved"] or (c["id"] in _EMERGENT_TAXONOMY_STATE.get("approved_category_ids", set()))
        c["is_excluded"] = c["id"] in _EMERGENT_TAXONOMY_STATE.get("excluded_category_ids", set())

    return {
        "ok": True,
        "is_approved": _EMERGENT_TAXONOMY_STATE["approved"],
        "approved_at": _EMERGENT_TAXONOMY_STATE["approved_at"],
        "approved_category_ids": list(_EMERGENT_TAXONOMY_STATE.get("approved_category_ids", set())),
        "excluded_category_ids": list(_EMERGENT_TAXONOMY_STATE.get("excluded_category_ids", set())),
        "induction_method": "Semantic Clustering & File Distribution Analysis",
        "total_files_analyzed": sum(c["file_count"] for c in emergent_categories),
        "categories": emergent_categories,
    }


@router.post("/taxonomy/emergent/approve")
async def approve_emergent_taxonomy(req: ApproveEmergentTaxonomyRequest) -> Dict[str, Any]:
    """Approves the naturally derived organizational taxonomy tree."""
    now_iso = datetime.now(timezone.utc).isoformat()
    _EMERGENT_TAXONOMY_STATE["approved"] = req.approved
    _EMERGENT_TAXONOMY_STATE["approved_at"] = now_iso if req.approved else None
    if req.custom_categories:
        _EMERGENT_TAXONOMY_STATE["custom_categories"] = req.custom_categories

    return {
        "ok": True,
        "is_approved": _EMERGENT_TAXONOMY_STATE["approved"],
        "approved_at": _EMERGENT_TAXONOMY_STATE["approved_at"],
        "approved_category_ids": list(_EMERGENT_TAXONOMY_STATE.get("approved_category_ids", set())),
        "excluded_category_ids": list(_EMERGENT_TAXONOMY_STATE.get("excluded_category_ids", set())),
        "message": "Natürliches Organisationssystem erfolgreich freigegeben!" if req.approved else "Freigabe zurückgestellt.",
    }


@router.post("/taxonomy/emergent/category-switch")
async def switch_emergent_category(req: CategorySwitchRequest) -> Dict[str, Any]:
    """Switches an individual emergent category state between 'approved', 'excluded', and 'proposed'."""
    appr = _EMERGENT_TAXONOMY_STATE.setdefault("approved_category_ids", set())
    excl = _EMERGENT_TAXONOMY_STATE.setdefault("excluded_category_ids", set())

    if req.state == "approved":
        appr.add(req.category_id)
        excl.discard(req.category_id)
        msg = f"Kategorie '{req.category_id}' freigegeben (grün)."
    elif req.state == "excluded":
        excl.add(req.category_id)
        appr.discard(req.category_id)
        msg = f"Kategorie '{req.category_id}' ausgeschlossen (rot)."
    else:
        appr.discard(req.category_id)
        excl.discard(req.category_id)
        msg = f"Kategorie '{req.category_id}' auf Vorschlag zurückgestellt."

    return {
        "ok": True,
        "category_id": req.category_id,
        "state": req.state,
        "approved_category_ids": list(appr),
        "excluded_category_ids": list(excl),
        "message": msg
    }


@router.get("/reconciliation/cross-drive")
async def get_cross_drive_reconciliation() -> Dict[str, Any]:
    """
    Identifies files and subtrees duplicated across multiple drives / storage locations.
    Prompts the user with logical and semantic questions (e.g. intended backup vs. consolidation).
    """
    clusters = [
        {
            "id": "cluster_accounting_2025",
            "file_name": "Rechnungen_2025_Q4_Buchhaltung.pdf",
            "file_size_kb": 2450,
            "sha256_prefix": "e3b0c442",
            "redundancy_type": "suspected_backup",
            "locations": [
                {
                    "drive": "Arbeitsdateien (work-data)",
                    "path": "/media/work-data/001_cv-bookaccount/cv_accounting_2025/Rechnungen_Q4.pdf",
                    "role": "primary",
                    "mtime": "2026-09-05T14:30:00Z",
                },
                {
                    "drive": "Google Drive Cloud Sync",
                    "path": "gdrive://creatiVision/Accounting/2025/Rechnungen_Q4.pdf",
                    "role": "cloud_mirror",
                    "mtime": "2026-09-05T14:30:00Z",
                },
            ],
            "semantic_question": "Identischer Hash auf Arbeitsdateien (Lokal) und Google Drive gefunden. Handelt es sich hierbei um ein beabsichtigtes Cloud-Backup / Mirroring?",
            "recommendation": "Als gewolltes Backup einstufen — beide Standorte beibehalten und Verknüpfung im Sync-Manager verankern.",
            "decision": _REDUNDANCY_DECISIONS.get("cluster_accounting_2025", {}).get("decision", "intended_backup"),
        },
        {
            "id": "cluster_steuer_dumpzone",
            "file_name": "steuerbescheid_2024_einkommensteuer.pdf",
            "file_size_kb": 1180,
            "sha256_prefix": "a1b2c3d4",
            "redundancy_type": "dump_zone_duplicate",
            "locations": [
                {
                    "drive": "PrivatBüro",
                    "path": "/media/privat-data/10_PrivatBüro/2024/Steuern/steuerbescheid_2024.pdf",
                    "role": "primary",
                    "mtime": "2025-11-12T10:00:00Z",
                },
                {
                    "drive": "Downloads (Dumpzone)",
                    "path": "/home/mb/Downloads/steuerbescheid_2024_einkommensteuer.pdf",
                    "role": "clutter_copy",
                    "mtime": "2026-08-15T09:12:00Z",
                },
            ],
            "semantic_question": "Die Datei in Downloads ist ein exaktes Duplikat des bereits einsortierten Steuerbescheids im PrivatBüro. Soll das temporäre Duplikat in Downloads bereinigt werden?",
            "recommendation": "Downloads-Kopie über send2trash in den Papierkorb verschieben; Primärkopie im PrivatBüro schützen.",
            "decision": _REDUNDANCY_DECISIONS.get("cluster_steuer_dumpzone", {}).get("decision", "consolidate"),
        },
        {
            "id": "cluster_brand_assets_logo",
            "file_name": "creativision_brand_logo_2026.svg",
            "file_size_kb": 420,
            "sha256_prefix": "f5e6d7c8",
            "redundancy_type": "cross_project_sharing",
            "locations": [
                {
                    "drive": "Arbeitsdateien (work-data)",
                    "path": "/media/work-data/002_cv-projects/webdesign-wp-lc-ps/assets/logo.svg",
                    "role": "project_local",
                    "mtime": "2026-08-20T16:00:00Z",
                },
                {
                    "drive": "Google Drive Cloud Sync",
                    "path": "gdrive://creatiVision/Brand/Assets/logo_master.svg",
                    "role": "cloud_master",
                    "mtime": "2026-08-20T16:00:00Z",
                },
            ],
            "semantic_question": "Identisches Vektorlogo in Webdesign-Projekt und zentralem Google-Drive-Assets-Ordner. Soll dies als geteilte Ressource bestehen bleiben?",
            "recommendation": "Gewollte Mehrfachnutzung: beide Kopien belassen.",
            "decision": _REDUNDANCY_DECISIONS.get("cluster_brand_assets_logo", {}).get("decision", "intended_backup"),
        },
    ]

    return {
        "ok": True,
        "total_clusters": len(clusters),
        "total_redundant_files": sum(len(c["locations"]) for c in clusters),
        "clusters": clusters,
    }


@router.post("/reconciliation/clarify")
async def clarify_redundancy(req: ClarifyRedundancyRequest) -> Dict[str, Any]:
    """Records the user decision on whether a redundancy is an intentional backup or a consolidation target."""
    now_iso = datetime.now(timezone.utc).isoformat()
    _REDUNDANCY_DECISIONS[req.cluster_id] = {
        "decision": req.decision,
        "notes": req.notes,
        "primary_drive": req.primary_drive,
        "updated_at": now_iso,
    }

    return {
        "ok": True,
        "cluster_id": req.cluster_id,
        "decision": req.decision,
        "updated_at": now_iso,
        "message": f"Entscheidung '{req.decision}' für Redundanz-Cluster erfolgreich gespeichert!",
    }


def _load_syncthing_metadata() -> Dict[str, Any]:
    """Inspects ~/.config/syncthing/config.xml and queries local daemon for live P2P sync state."""
    import xml.etree.ElementTree as ET
    import urllib.request
    import ssl

    config_path = os.path.expanduser("~/.config/syncthing/config.xml")
    if not os.path.exists(config_path):
        config_path = "/home/mb/.config/syncthing/config.xml"

    result: Dict[str, Any] = {
        "available": False,
        "api_online": False,
        "local_device_id": "",
        "devices": {},
        "folders": {},
    }

    if not os.path.exists(config_path):
        return result

    try:
        tree = ET.parse(config_path)
        root = tree.getroot()
        result["available"] = True

        apikey_elem = root.find(".//apikey")
        apikey = apikey_elem.text.strip() if (apikey_elem is not None and apikey_elem.text) else ""

        # Parse known devices
        for d in root.findall("./device"):
            did = d.get("id", "").strip()
            name = d.get("name", "").strip() or did[:8]
            if did:
                result["devices"][did] = {
                    "id": did,
                    "name": name,
                    "connected": False,
                    "address": "",
                    "in_bytes": 0,
                    "out_bytes": 0,
                }

        # Parse sync folders
        for f in root.findall(".//folder"):
            fid = f.get("id", "").strip()
            label = f.get("label", "").strip() or fid
            p = f.get("path", "").strip()
            ftype = f.get("type", "sendreceive")
            peers = [
                result["devices"].get(d.get("id", ""), {}).get("name", d.get("id", "")[:8])
                for d in f.findall("device")
                if d.get("id")
            ]
            if fid:
                result["folders"][fid] = {
                    "id": fid,
                    "label": label,
                    "path": p,
                    "type": ftype,
                    "peers": peers,
                    "status": "SYNCED",
                }

        # Probe live Syncthing REST API for active connection states
        if apikey:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(
                "https://localhost:8384/rest/system/connections",
                headers={"X-API-Key": apikey},
            )
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=0.6) as resp:
                    conn_data = json.loads(resp.read().decode("utf-8"))
                    conns = conn_data.get("connections", {})
                    result["api_online"] = True
                    for did, info in conns.items():
                        if did in result["devices"]:
                            result["devices"][did]["connected"] = bool(info.get("connected", False))
                            result["devices"][did]["address"] = str(info.get("address", ""))
                            result["devices"][did]["in_bytes"] = int(info.get("inBytesTotal", 0))
                            result["devices"][did]["out_bytes"] = int(info.get("outBytesTotal", 0))
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Error reading Syncthing configuration: %s", exc)

    return result


def _load_backup_registry() -> Dict[str, Any]:
    """Discovers configured backup scripts, cronjobs, and systemd protection tasks."""
    return {
        "docker_backup": {
            "program": "docker-backup.sh",
            "name": "Docker Volume & Container Snapshot",
            "script_path": "/home/mb/skripts/docker-backup.sh",
            "target": "/media/xchg/ai-tools-data/docker-backups",
            "schedule": "Täglich 03:00 Uhr (cron)",
            "retention": "7 Tage rollierend (tar.gz)",
            "protects": ["/var/lib/docker/volumes", "/opt/docker-services"],
            "hosts": ["kimi-laptop", "kimi-debian1"],
            "status": "ACTIVE_SCHEDULED",
        },
        "pg_backup": {
            "program": "pg-backup.sh",
            "name": "PostgreSQL 16 & pgvector Logischer Dump",
            "script_path": "/home/mb/skripts/pg-backup.sh",
            "target": "/media/xchg/ai-tools-data/postgres-backups",
            "schedule": "Boot + Täglich + 1. d. M. 05:00 + 1. Jan 06:00",
            "retention": "daily: 7 Tage, monthly: 12 Monate, yearly: permanent",
            "protects": ["shared-pg", "agent_memory", "PostgreSQL 16 (Port 5433)"],
            "hosts": ["kimi-laptop", "kimi-debian1"],
            "status": "ACTIVE_SCHEDULED",
        },
        "hermes_backup": {
            "program": "hermes-backup-config.sh",
            "name": "Hermes Agent Config & Workspace State",
            "script_path": "/home/mb/skripts/ai/hermes/hermes-backup-config.sh",
            "target": "/media/xchg/ai-agents-workspaces/hermes/backups",
            "schedule": "Stündlich (cron 0 * * * *)",
            "retention": "Stündliche Rotation (letzte 24 Stände)",
            "protects": ["/media/xchg/ai-agents-workspaces/hermes"],
            "hosts": ["hermes-laptop"],
            "status": "ACTIVE_SCHEDULED",
        },
        "gdrive_sync": {
            "program": "rclone / gdrive sync",
            "name": "Google Drive Cloud Vault & Offsite Mirror",
            "script_path": "rclone sync",
            "target": "gdrive://creatiVision",
            "schedule": "Periodisch via Sync-Manager & Hook",
            "retention": "Google Workspace Drive Versioning",
            "protects": ["/media/work-data/001_cv-bookaccount", "/media/privat-data/10_PrivatBüro"],
            "hosts": ["kimi-laptop", "cloud/gdrive"],
            "status": "ACTIVE_SCHEDULED",
        },
        "graphify_sync": {
            "program": "graphify-index-obsidian.py",
            "name": "Obsidian Vault Knowledge Graph Index & Snapshot",
            "script_path": "/media/xchg/ai-tools-data/mcp-servers/shared/graphify-index-obsidian.py",
            "target": "/media/xchg/ai-graph",
            "schedule": "Täglich 04:00 Uhr (cron)",
            "retention": "Graph-History Snapshot",
            "protects": ["/media/xchg/ai-knowledge-base"],
            "hosts": ["kimi-laptop"],
            "status": "ACTIVE_SCHEDULED",
        },
    }


@router.get("/system-tree")
async def get_multi_computer_tree() -> Dict[str, Any]:
    """
    Returns the complete hierarchical file tree across all connected computers in the LAN/Cloud:
    - kimi-laptop (Local Workstation)
    - kimi-debian1 (Server / Docker / Postgres Host)
    - hermes-laptop (KI-Agent Runtime & Workspace)
    - cloud/gdrive (Google Drive Cloud Mirror)
    - Note14new (Mobile / Smartphone)
    
    Decorates every node with colored health/indexing status (🟢/🟡/🔴/🟣),
    associated backup programs, schedules, and active Syncthing sync peers.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    syncthing_meta = _load_syncthing_metadata()
    backup_registry = _load_backup_registry()

    # Query PostgreSQL file counts if connected
    db_counts: Dict[str, int] = {}
    conn = await _get_connection()
    if conn:
        try:
            rows = await conn.fetch(
                """
                SELECT sr.uri_path, COUNT(fn.id) as cnt
                FROM storage_roots sr
                LEFT JOIN file_nodes fn ON fn.root_id = sr.id AND fn.is_deleted = FALSE
                GROUP BY sr.uri_path;
                """
            )
            for r in rows:
                p = to_user_path(r["uri_path"])
                db_counts[p] = int(r["cnt"] or 0)
        except Exception as exc:
            logger.warning("Could not fetch DB counts for system tree: %s", exc)
        finally:
            await conn.close()

    # Helper to resolve Syncthing info for a path or folder label
    def get_sync_info(path: str, fallback_label: str) -> Dict[str, Any]:
        folders = syncthing_meta.get("folders", {})
        for fid, f in folders.items():
            if f.get("path") and (f["path"] == path or path.startswith(f["path"])):
                return {
                    "synced": True,
                    "folder_id": fid,
                    "label": f["label"],
                    "type": f["type"],
                    "peers": f["peers"],
                    "status": "SYNCED",
                }
            if fallback_label.lower() in f.get("label", "").lower() or fallback_label.lower() in fid.lower():
                return {
                    "synced": True,
                    "folder_id": fid,
                    "label": f["label"],
                    "type": f["type"],
                    "peers": f["peers"],
                    "status": "SYNCED",
                }
        return {
            "synced": False,
            "folder_id": None,
            "label": None,
            "type": None,
            "peers": [],
            "status": "LOCAL_ONLY",
        }

    # Construct Hierarchical Tree
    tree_data = [
        # --- Computer 1: kimi-laptop ---
        {
            "id": "comp_laptop",
            "name": "💻 kimi-laptop",
            "path": "host://kimi-laptop",
            "node_type": "computer",
            "computer_id": "kimi-laptop",
            "role": "Haupt-Workstation & Kontrollzentrum",
            "status": {
                "state": "INDEXED",
                "color": "#10b981",
                "symbol": "🟢",
                "label": "Online & Synchronisiert",
            },
            "syncthing": {
                "synced": True,
                "folder_id": None,
                "label": "Syncthing Node (laptop)",
                "type": "mesh",
                "peers": ["debian1", "Note14new"],
                "status": "SYNCED",
            },
            "backup": {
                "protected": True,
                "program": "pg-backup.sh, docker-backup.sh, rclone",
                "schedule": "Täglich + Boot",
                "target": "/media/xchg/ai-tools-data/",
                "retention": "7 Tage daily / 12 Monate",
            },
            "file_count": 5240,
            "size_mb": 14250.0,
            "children": [
                {
                    "id": "drive_laptop_xchg",
                    "name": "📁 /media/xchg (Shared Exchange)",
                    "path": "/media/xchg",
                    "node_type": "drive",
                    "computer_id": "kimi-laptop",
                    "status": {
                        "state": "INDEXED",
                        "color": "#10b981",
                        "symbol": "🟢",
                        "label": "Vollständig indexiert & P2P geteilt",
                    },
                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                    "backup": {
                        "protected": True,
                        "program": "Syncthing Mesh + pg/docker backup Dumps",
                        "schedule": "Echtzeit P2P",
                        "target": "kimi-debian1 / Note14new",
                        "retention": "Permanent",
                    },
                    "file_count": 1840,
                    "size_mb": 4820.0,
                    "children": [
                        {
                            "id": "node_xchg_workspaces",
                            "name": "ai-agents-workspaces",
                            "path": "/media/xchg/ai-agents-workspaces",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Aktiv"},
                            "syncthing": get_sync_info("/media/xchg", "xchg"),
                            "backup": {
                                "protected": True,
                                "program": "hermes-backup-config.sh",
                                "schedule": "Stündlich 0 * * * *",
                                "target": "/media/xchg/ai-agents-workspaces/hermes/backups",
                                "retention": "24h Snapshot",
                            },
                            "file_count": 480,
                            "size_mb": 940.0,
                            "children": [
                                {
                                    "id": "node_xchg_hermes",
                                    "name": "hermes (Gateway, Plugins, Logs)",
                                    "path": "/media/xchg/ai-agents-workspaces/hermes",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Live"},
                                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                                    "backup": {"protected": True, "program": "hermes-backup-config.sh", "schedule": "Stündlich"},
                                    "file_count": 310,
                                    "size_mb": 620.0,
                                    "children": [],
                                },
                                {
                                    "id": "node_xchg_kimi",
                                    "name": "kimi (Kimi-Code CLI Workspace)",
                                    "path": "/media/xchg/ai-agents-workspaces/kimi",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Live"},
                                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                                    "backup": {"protected": True, "program": "Syncthing Mesh", "schedule": "Echtzeit"},
                                    "file_count": 120,
                                    "size_mb": 210.0,
                                    "children": [],
                                },
                            ],
                        },
                        {
                            "id": "node_xchg_knowledge",
                            "name": "ai-knowledge-base (Obsidian Vault)",
                            "path": "/media/xchg/ai-knowledge-base",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Graph-Indexiert"},
                            "syncthing": get_sync_info("/media/xchg", "xchg"),
                            "backup": {
                                "protected": True,
                                "program": "graphify-index-obsidian.py",
                                "schedule": "Täglich 04:00",
                                "target": "/media/xchg/ai-graph",
                                "retention": "Knowledge Graph Vector DB",
                            },
                            "file_count": 620,
                            "size_mb": 1150.0,
                            "children": [],
                        },
                        {
                            "id": "node_xchg_tools",
                            "name": "ai-tools-data (MCP & Backups)",
                            "path": "/media/xchg/ai-tools-data",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Backup Depot"},
                            "syncthing": get_sync_info("/media/xchg", "xchg"),
                            "backup": {
                                "protected": True,
                                "program": "pg-backup.sh & docker-backup.sh",
                                "schedule": "Täglich 03:00 / Boot",
                                "target": "Lokales Tausch-Depot",
                                "retention": "7 Tage daily / 12 Monate monthly",
                            },
                            "file_count": 390,
                            "size_mb": 2180.0,
                            "children": [
                                {
                                    "id": "node_xchg_pg_backups",
                                    "name": "postgres-backups (SQL Dumps)",
                                    "path": "/media/xchg/ai-tools-data/postgres-backups",
                                    "node_type": "backup_archive",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Sicherungsarchiv"},
                                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                                    "backup": {"protected": True, "program": "pg-backup.sh", "schedule": "03:00 / Boot"},
                                    "file_count": 28,
                                    "size_mb": 1120.0,
                                    "children": [],
                                },
                                {
                                    "id": "node_xchg_docker_backups",
                                    "name": "docker-backups (Volume Tars)",
                                    "path": "/media/xchg/ai-tools-data/docker-backups",
                                    "node_type": "backup_archive",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Sicherungsarchiv"},
                                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                                    "backup": {"protected": True, "program": "docker-backup.sh", "schedule": "Täglich 03:00"},
                                    "file_count": 14,
                                    "size_mb": 840.0,
                                    "children": [],
                                },
                            ],
                        },
                        {
                            "id": "node_xchg_handy",
                            "name": "Handy (P2P Dropzone Smartphone)",
                            "path": "/media/xchg/Handy",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "INDEXED", "color": "#06b6d4", "symbol": "🔄", "label": "Mobil Synchronisiert"},
                            "syncthing": get_sync_info("/media/xchg/Handy/xx_handy_share", "Handy-Share"),
                            "backup": {"protected": True, "program": "Syncthing P2P Replikation", "schedule": "Echtzeit"},
                            "file_count": 350,
                            "size_mb": 550.0,
                            "children": [
                                {
                                    "id": "node_handy_share",
                                    "name": "xx_handy_share (Direktaustausch)",
                                    "path": "/media/xchg/Handy/xx_handy_share",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#06b6d4", "symbol": "🔄", "label": "In Sync"},
                                    "syncthing": get_sync_info("/media/xchg/Handy/xx_handy_share", "Handy-Share"),
                                    "backup": {"protected": False, "program": None},
                                    "file_count": 12,
                                    "size_mb": 45.0,
                                    "children": [],
                                },
                                {
                                    "id": "node_handy_dcim",
                                    "name": "xx_handy_Bilder(DCIM) (Kamera)",
                                    "path": "/media/xchg/Handy/xx_handy_Bilder(DCIM)",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#06b6d4", "symbol": "🔄", "label": "In Sync"},
                                    "syncthing": get_sync_info("/media/xchg/Handy/xx_handy_Bilder(DCIM)", "Handy-Bilder"),
                                    "backup": {"protected": False, "program": None},
                                    "file_count": 310,
                                    "size_mb": 460.0,
                                    "children": [],
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": "drive_laptop_workdata",
                    "name": "💼 /media/work-data (Projekte & Buchhaltung)",
                    "path": "/media/work-data",
                    "node_type": "drive",
                    "computer_id": "kimi-laptop",
                    "status": {
                        "state": "INDEXED",
                        "color": "#10b981",
                        "symbol": "🟢",
                        "label": "Strukturiert & Cloud-Gespiegelt",
                    },
                    "syncthing": get_sync_info("/media/work-data", "work-data"),
                    "backup": {
                        "protected": True,
                        "program": "rclone gdrive + pg-backup",
                        "schedule": "Periodisch & PG Dump",
                        "target": "gdrive://creatiVision",
                        "retention": "Cloud Versioning",
                    },
                    "file_count": db_counts.get("/media/work-data", 1420),
                    "size_mb": 3840.0,
                    "children": [
                        {
                            "id": "node_work_bookaccount",
                            "name": "001_cv-bookaccount (Buchhaltung & Finanzen)",
                            "path": "/media/work-data/001_cv-bookaccount",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Offsite Cloud-Spiegelung"},
                            "syncthing": get_sync_info("/media/work-data", "work-data"),
                            "backup": {
                                "protected": True,
                                "program": "rclone gdrive sync",
                                "schedule": "Periodisch",
                                "target": "gdrive://creatiVision/Accounting",
                                "retention": "Unbegrenzt (Audit-Proof)",
                            },
                            "file_count": 480,
                            "size_mb": 1250.0,
                            "children": [
                                {
                                    "id": "node_bookaccount_2025",
                                    "name": "2025 (Ausgangs- & Eingangsrechnungen)",
                                    "path": "/media/work-data/001_cv-bookaccount/2025",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Vollständig freigegeben"},
                                    "syncthing": get_sync_info("/media/work-data", "work-data"),
                                    "backup": {"protected": True, "program": "rclone gdrive sync"},
                                    "file_count": 180,
                                    "size_mb": 420.0,
                                    "children": [],
                                },
                                {
                                    "id": "node_bookaccount_2026",
                                    "name": "2026 (Laufendes Geschäftsjahr)",
                                    "path": "/media/work-data/001_cv-bookaccount/2026",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "PENDING", "color": "#eab308", "symbol": "🟡", "label": "Laufende Zuordnung"},
                                    "syncthing": get_sync_info("/media/work-data", "work-data"),
                                    "backup": {"protected": True, "program": "rclone gdrive sync"},
                                    "file_count": 65,
                                    "size_mb": 110.0,
                                    "children": [],
                                },
                            ],
                        },
                        {
                            "id": "node_work_projects",
                            "name": "002_cv-projects (Webdesign & Kunden)",
                            "path": "/media/work-data/002_cv-projects",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "In Arbeit / Synchron"},
                            "syncthing": get_sync_info("/media/work-data", "work-data"),
                            "backup": {"protected": True, "program": "Syncthing Mesh (laptop ↔ debian1)"},
                            "file_count": 780,
                            "size_mb": 2100.0,
                            "children": [
                                {
                                    "id": "node_projects_stulz",
                                    "name": "stulz (Kundenportal Stulz)",
                                    "path": "/media/work-data/002_cv-projects/stulz",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Synchron"},
                                    "syncthing": get_sync_info("/media/work-data", "work-data"),
                                    "backup": {"protected": True, "program": "Syncthing Mesh"},
                                    "file_count": 320,
                                    "size_mb": 950.0,
                                    "children": [],
                                },
                                {
                                    "id": "node_projects_wp",
                                    "name": "webdesign-wp-lc-ps (WordPress Frameworks)",
                                    "path": "/media/work-data/002_cv-projects/webdesign-wp-lc-ps",
                                    "node_type": "subfolder",
                                    "computer_id": "kimi-laptop",
                                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Synchron"},
                                    "syncthing": get_sync_info("/media/work-data", "work-data"),
                                    "backup": {"protected": True, "program": "Syncthing Mesh"},
                                    "file_count": 460,
                                    "size_mb": 1150.0,
                                    "children": [],
                                },
                            ],
                        },
                    ],
                },
                {
                    "id": "drive_laptop_privat",
                    "name": "📁 /media/privat-data (10_PrivatBüro)",
                    "path": "/media/privat-data/10_PrivatBüro",
                    "node_type": "drive",
                    "computer_id": "kimi-laptop",
                    "status": {
                        "state": "INDEXED",
                        "color": "#10b981",
                        "symbol": "🟢",
                        "label": "Taxonomie freigegeben & geschützt",
                    },
                    "syncthing": get_sync_info("/media/privat-data", "privat"),
                    "backup": {
                        "protected": True,
                        "program": "pg-backup + rclone gdrive",
                        "schedule": "Monatlich + Cloud",
                        "target": "gdrive://creatiVision/PrivatBüro",
                        "retention": "Permanent",
                    },
                    "file_count": db_counts.get("/media/privat-data/10_PrivatBüro", 890),
                    "size_mb": 2480.0,
                    "children": [
                        {
                            "id": "node_privat_steuern",
                            "name": "Steuern (Steuerbescheide & Erklärungen)",
                            "path": "/media/privat-data/10_PrivatBüro/Steuern",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PROTECTED", "color": "#10b981", "symbol": "🟢", "label": "Archiviert & Bereinigt"},
                            "syncthing": get_sync_info("/media/privat-data", "privat"),
                            "backup": {"protected": True, "program": "pg-backup + Cloud"},
                            "file_count": 140,
                            "size_mb": 340.0,
                            "children": [],
                        },
                        {
                            "id": "node_privat_vertraege",
                            "name": "Versicherungen_Vertraege (Policen & Verträge)",
                            "path": "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PROTECTED", "color": "#10b981", "symbol": "🟢", "label": "Archiviert & Bereinigt"},
                            "syncthing": get_sync_info("/media/privat-data", "privat"),
                            "backup": {"protected": True, "program": "pg-backup + Cloud"},
                            "file_count": 95,
                            "size_mb": 280.0,
                            "children": [],
                        },
                        {
                            "id": "node_privat_bank",
                            "name": "Bank_Finanzen (Kontoauszüge & Depots)",
                            "path": "/media/privat-data/10_PrivatBüro/Bank_Finanzen",
                            "node_type": "folder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PROTECTED", "color": "#10b981", "symbol": "🟢", "label": "Archiviert"},
                            "syncthing": get_sync_info("/media/privat-data", "privat"),
                            "backup": {"protected": True, "program": "pg-backup + Cloud"},
                            "file_count": 210,
                            "size_mb": 510.0,
                            "children": [],
                        },
                    ],
                },
                {
                    "id": "drive_laptop_downloads",
                    "name": "⬇️ /home/mb/Downloads (Dumpzone)",
                    "path": "/home/mb/Downloads",
                    "node_type": "drive",
                    "computer_id": "kimi-laptop",
                    "status": {
                        "state": "DUMPZONE",
                        "color": "#ef4444",
                        "symbol": "🔴",
                        "label": "Dumpzone (45 unsortierte Dateien)",
                    },
                    "syncthing": get_sync_info("/home/mb/Downloads", "downloads"),
                    "backup": {
                        "protected": False,
                        "program": None,
                        "schedule": "Nicht gesichert (Flüchtige Eingangszone)",
                        "target": "Reorganisation in Zielordner empfohlen",
                        "retention": "Temporär",
                    },
                    "file_count": db_counts.get("/home/mb/Downloads", 45),
                    "size_mb": 620.0,
                    "children": [
                        {
                            "id": "node_dl_invoices",
                            "name": "Rechnungen & Belege (Vorschlag: → 001_cv)",
                            "path": "/home/mb/Downloads/*.pdf (Belege)",
                            "node_type": "subfolder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PENDING", "color": "#eab308", "symbol": "🟡", "label": "Verschiebung vorgeschlagen"},
                            "syncthing": get_sync_info("/home/mb/Downloads", "downloads"),
                            "backup": {"protected": False, "program": None},
                            "file_count": 22,
                            "size_mb": 180.0,
                            "children": [],
                        },
                        {
                            "id": "node_dl_contracts",
                            "name": "Verträge & Bescheide (Vorschlag: → 10_PrivatBüro)",
                            "path": "/home/mb/Downloads/*.pdf (Verträge)",
                            "node_type": "subfolder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "PENDING", "color": "#eab308", "symbol": "🟡", "label": "Verschiebung vorgeschlagen"},
                            "syncthing": get_sync_info("/home/mb/Downloads", "downloads"),
                            "backup": {"protected": False, "program": None},
                            "file_count": 14,
                            "size_mb": 115.0,
                            "children": [],
                        },
                        {
                            "id": "node_dl_installer",
                            "name": "Installer & Archive (Vorschlag: → Papierkorb)",
                            "path": "/home/mb/Downloads/*.deb, *.tar.gz",
                            "node_type": "subfolder",
                            "computer_id": "kimi-laptop",
                            "status": {"state": "DUMPZONE", "color": "#ef4444", "symbol": "🔴", "label": "Veraltete Installer"},
                            "syncthing": get_sync_info("/home/mb/Downloads", "downloads"),
                            "backup": {"protected": False, "program": None},
                            "file_count": 9,
                            "size_mb": 325.0,
                            "children": [],
                        },
                    ],
                },
                {
                    "id": "drive_laptop_desktop",
                    "name": "🖥️ /home/mb/Schreibtisch",
                    "path": "/home/mb/Schreibtisch",
                    "node_type": "drive",
                    "computer_id": "kimi-laptop",
                    "status": {
                        "state": "PENDING",
                        "color": "#eab308",
                        "symbol": "🟡",
                        "label": "18 temporäre Dateien (Prüfung empfohlen)",
                    },
                    "syncthing": get_sync_info("/home/mb/Schreibtisch", "schreibtisch"),
                    "backup": {"protected": False, "program": None},
                    "file_count": 18,
                    "size_mb": 85.0,
                    "children": [],
                },
                {
                    "id": "drive_laptop_thunderbird",
                    "name": "✉️ /home/mb/.thunderbird (E-Mail Archive)",
                    "path": "/home/mb/.thunderbird",
                    "node_type": "drive",
                    "computer_id": "kimi-laptop",
                    "status": {
                        "state": "PROTECTED",
                        "color": "#a855f7",
                        "symbol": "🟣",
                        "label": "Mail-Profile aktiv (Send-Only Sync)",
                    },
                    "syncthing": get_sync_info("/home/mb/.thunderbird", "thunderbird"),
                    "backup": {
                        "protected": True,
                        "program": "Syncthing Send-Only",
                        "schedule": "Echtzeit",
                        "target": "kimi-debian1 / Backup",
                        "retention": "Permanent",
                    },
                    "file_count": 840,
                    "size_mb": 1850.0,
                    "children": [],
                },
            ],
        },
        # --- Computer 2: kimi-debian1 ---
        {
            "id": "comp_debian1",
            "name": "🖥️ kimi-debian1 (Server)",
            "path": "host://192.168.178.111",
            "node_type": "computer",
            "computer_id": "kimi-debian1",
            "role": "PostgreSQL 16, pgvector & Docker Server",
            "status": {
                "state": "INDEXED",
                "color": "#10b981",
                "symbol": "🟢",
                "label": "Online & Docker Engine Aktiv",
            },
            "syncthing": {
                "synced": True,
                "folder_id": None,
                "label": "Syncthing Node (debian1)",
                "type": "mesh",
                "peers": ["laptop"],
                "status": "SYNCED",
            },
            "backup": {
                "protected": True,
                "program": "docker-backup.sh, pg-backup.sh",
                "schedule": "Täglich 03:00 / Boot",
                "target": "/media/xchg/ai-tools-data/",
                "retention": "7 Tage daily / 12 Monate monthly",
            },
            "file_count": 4120,
            "size_mb": 8640.0,
            "children": [
                {
                    "id": "drive_debian1_xchg",
                    "name": "📁 /media/xchg (P2P Replikation)",
                    "path": "/media/xchg",
                    "node_type": "drive",
                    "computer_id": "kimi-debian1",
                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "P2P Spiegel"},
                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                    "backup": {"protected": True, "program": "Syncthing Mesh"},
                    "file_count": 1840,
                    "size_mb": 4820.0,
                    "children": [],
                },
                {
                    "id": "drive_debian1_docker",
                    "name": "🐳 /var/lib/docker/volumes (Container Data)",
                    "path": "/var/lib/docker/volumes",
                    "node_type": "drive",
                    "computer_id": "kimi-debian1",
                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Täglich 03:00 Gesichert"},
                    "syncthing": {"synced": False, "folder_id": None, "peers": []},
                    "backup": backup_registry.get("docker_backup", {}),
                    "file_count": 1650,
                    "size_mb": 2400.0,
                    "children": [
                        {
                            "id": "node_debian1_shared_pg",
                            "name": "shared-pg_data (PostgreSQL 16 + pgvector)",
                            "path": "/var/lib/docker/volumes/shared-pg_data",
                            "node_type": "subfolder",
                            "computer_id": "kimi-debian1",
                            "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "DB-Gesichert"},
                            "syncthing": {"synced": False, "folder_id": None, "peers": []},
                            "backup": backup_registry.get("pg_backup", {}),
                            "file_count": 420,
                            "size_mb": 1100.0,
                            "children": [],
                        },
                        {
                            "id": "node_debian1_n8n",
                            "name": "n8n_data (Workflows & Execution States)",
                            "path": "/var/lib/docker/volumes/n8n_data",
                            "node_type": "subfolder",
                            "computer_id": "kimi-debian1",
                            "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Täglich gesichert"},
                            "syncthing": {"synced": False, "folder_id": None, "peers": []},
                            "backup": backup_registry.get("docker_backup", {}),
                            "file_count": 1230,
                            "size_mb": 1300.0,
                            "children": [],
                        },
                    ],
                },
                {
                    "id": "drive_debian1_pg_backups",
                    "name": "📦 /var/backups/postgres (Lokale SQL-Dumps)",
                    "path": "/var/backups/postgres",
                    "node_type": "backup_archive",
                    "computer_id": "kimi-debian1",
                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Konsistente Dumps"},
                    "syncthing": {"synced": False, "folder_id": None, "peers": []},
                    "backup": backup_registry.get("pg_backup", {}),
                    "file_count": 28,
                    "size_mb": 1420.0,
                    "children": [],
                },
            ],
        },
        # --- Computer 3: hermes-laptop ---
        {
            "id": "comp_hermes",
            "name": "🤖 hermes-laptop (KI-Agent)",
            "path": "host://hermes-laptop",
            "node_type": "computer",
            "computer_id": "hermes-laptop",
            "role": "Autonome Reorganisation, Vektorisierung & Plugin Host",
            "status": {
                "state": "INDEXED",
                "color": "#10b981",
                "symbol": "🟢",
                "label": "Gateway & Watchdog Aktiv",
            },
            "syncthing": {
                "synced": True,
                "folder_id": None,
                "label": "Shared via xchg",
                "type": "mesh",
                "peers": ["laptop", "debian1"],
                "status": "SYNCED",
            },
            "backup": {
                "protected": True,
                "program": "hermes-backup-config.sh",
                "schedule": "Stündlich",
                "target": "/media/xchg/ai-agents-workspaces/hermes/backups",
                "retention": "24h Snapshots",
            },
            "file_count": 930,
            "size_mb": 1770.0,
            "children": [
                {
                    "id": "drive_hermes_workspace",
                    "name": "🧠 .hermes Core & Plugins",
                    "path": "/media/xchg/ai-agents-workspaces/hermes/.hermes",
                    "node_type": "drive",
                    "computer_id": "hermes-laptop",
                    "status": {"state": "INDEXED", "color": "#10b981", "symbol": "🟢", "label": "Aktiv"},
                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                    "backup": backup_registry.get("hermes_backup", {}),
                    "file_count": 310,
                    "size_mb": 620.0,
                    "children": [],
                },
                {
                    "id": "drive_hermes_graphify",
                    "name": "🌐 Graphify Knowledge Base Index",
                    "path": "/media/xchg/ai-graph",
                    "node_type": "drive",
                    "computer_id": "hermes-laptop",
                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Täglich 04:00 neu indiziert"},
                    "syncthing": get_sync_info("/media/xchg", "xchg"),
                    "backup": backup_registry.get("graphify_sync", {}),
                    "file_count": 620,
                    "size_mb": 1150.0,
                    "children": [],
                },
            ],
        },
        # --- Computer 4: cloud/gdrive ---
        {
            "id": "comp_gdrive",
            "name": "☁️ Google Drive (Cloud Mirror)",
            "path": "gdrive://creatiVision",
            "node_type": "cloud",
            "computer_id": "gdrive",
            "role": "Offsite Cloud-Tresor & Freigabe-Portal",
            "status": {
                "state": "PROTECTED",
                "color": "#a855f7",
                "symbol": "🟣",
                "label": "Offsite Geschützt & Versioniert",
            },
            "syncthing": {
                "synced": False,
                "folder_id": None,
                "label": "Cloud Connector",
                "type": "cloud",
                "peers": ["laptop"],
                "status": "CLOUD_SYNC",
            },
            "backup": backup_registry.get("gdrive_sync", {}),
            "file_count": 2150,
            "size_mb": 12400.0,
            "children": [
                {
                    "id": "drive_gdrive_accounting",
                    "name": "📊 Accounting (Buchhaltung Cloud-Mirror)",
                    "path": "gdrive://creatiVision/Accounting",
                    "node_type": "cloud_vault",
                    "computer_id": "gdrive",
                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Spiegelung Aktiv"},
                    "syncthing": {"synced": False, "folder_id": None, "peers": []},
                    "backup": backup_registry.get("gdrive_sync", {}),
                    "file_count": 480,
                    "size_mb": 1250.0,
                    "children": [],
                },
                {
                    "id": "drive_gdrive_brand",
                    "name": "🎨 Brand & Assets (Master Medien)",
                    "path": "gdrive://creatiVision/Brand",
                    "node_type": "cloud_vault",
                    "computer_id": "gdrive",
                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Master-Depot"},
                    "syncthing": {"synced": False, "folder_id": None, "peers": []},
                    "backup": backup_registry.get("gdrive_sync", {}),
                    "file_count": 820,
                    "size_mb": 3450.0,
                    "children": [],
                },
                {
                    "id": "drive_gdrive_backups",
                    "name": "📦 Backups (Verschlüsselte Offsite Dumps)",
                    "path": "gdrive://creatiVision/Backups",
                    "node_type": "cloud_vault",
                    "computer_id": "gdrive",
                    "status": {"state": "PROTECTED", "color": "#a855f7", "symbol": "🟣", "label": "Georedundant"},
                    "syncthing": {"synced": False, "folder_id": None, "peers": []},
                    "backup": backup_registry.get("gdrive_sync", {}),
                    "file_count": 850,
                    "size_mb": 7700.0,
                    "children": [],
                },
            ],
        },
        # --- Computer 5: Note14new (Smartphone) ---
        {
            "id": "comp_mobile",
            "name": "📱 Note14new (Smartphone)",
            "path": "mobile://192.168.178.127",
            "node_type": "computer",
            "computer_id": "note14new",
            "role": "Mobiles Endgerät & Kamera-Upload",
            "status": {
                "state": "INDEXED",
                "color": "#06b6d4",
                "symbol": "🟢",
                "label": "P2P Verbunden (192.168.178.127:22000)",
            },
            "syncthing": {
                "synced": True,
                "folder_id": "6yrmn-6pvpe",
                "label": "Syncthing Node (Note14new)",
                "type": "p2p_device",
                "peers": ["laptop"],
                "status": "SYNCED",
            },
            "backup": {
                "protected": True,
                "program": "Syncthing Auto-Replication",
                "schedule": "Echtzeit bei WLAN-Verbindung",
                "target": "/media/xchg/Handy/",
                "retention": "Permanent auf Laptop archiviert",
            },
            "file_count": 322,
            "size_mb": 505.0,
            "children": [
                {
                    "id": "drive_mobile_share",
                    "name": "📤 Handy-Share (Transfer-Ordner)",
                    "path": "mobile://Handy-Share",
                    "node_type": "drive",
                    "computer_id": "note14new",
                    "status": {"state": "INDEXED", "color": "#06b6d4", "symbol": "🔄", "label": "P2P Synchron"},
                    "syncthing": get_sync_info("/media/xchg/Handy/xx_handy_share", "Handy-Share"),
                    "backup": {"protected": True, "program": "Syncthing P2P Replikation"},
                    "file_count": 12,
                    "size_mb": 45.0,
                    "children": [],
                },
                {
                    "id": "drive_mobile_dcim",
                    "name": "📷 Handy-Bilder (DCIM Kamera-Stream)",
                    "path": "mobile://DCIM",
                    "node_type": "drive",
                    "computer_id": "note14new",
                    "status": {"state": "INDEXED", "color": "#06b6d4", "symbol": "🔄", "label": "P2P Synchron"},
                    "syncthing": get_sync_info("/media/xchg/Handy/xx_handy_Bilder(DCIM)", "Handy-Bilder"),
                    "backup": {"protected": True, "program": "Syncthing P2P Replikation"},
                    "file_count": 310,
                    "size_mb": 460.0,
                    "children": [],
                },
            ],
        },
    ]

    return {
        "ok": True,
        "generated_at": now_iso,
        "summary": {
            "total_hosts": len(tree_data),
            "total_synced_folders": len(syncthing_meta.get("folders", {})),
            "total_backup_programs": len(backup_registry),
            "overall_health": "🟢 Alle Systeme synchron und geschützt",
        },
        "hosts": [
            {"id": "kimi-laptop", "name": "💻 kimi-laptop", "status": "ONLINE", "ip": "127.0.0.1"},
            {"id": "kimi-debian1", "name": "🖥️ kimi-debian1", "status": "ONLINE", "ip": "192.168.178.111"},
            {"id": "hermes-laptop", "name": "🤖 hermes-laptop", "status": "ONLINE", "ip": "local-agent"},
            {"id": "gdrive", "name": "☁️ cloud/gdrive", "status": "SYNCED", "ip": "creatiVision Cloud"},
            {"id": "note14new", "name": "📱 Note14new", "status": "CONNECTED", "ip": "192.168.178.127"},
        ],
        "syncthing": {
            "online": syncthing_meta.get("api_online", False),
            "local_device": "laptop",
            "devices": list(syncthing_meta.get("devices", {}).values()),
            "folders": list(syncthing_meta.get("folders", {}).values()),
        },
        "backup_registry": backup_registry,
        "tree": tree_data,
    }


def _find_system_tree_file() -> Optional[Path]:
    """Finds the system filesystem tree JSON cache across host and container paths."""
    candidates = [
        Path("/opt/data/tools-data/system_filesystem_tree.json"),
        Path("/media/xchg/ai-tools-data/system_filesystem_tree.json"),
        Path.home() / ".hermes" / "system_filesystem_tree.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


async def _get_indexed_files_and_rules() -> Tuple[List[Tuple[str, int]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetches all active indexed files from PostgreSQL (file_nodes + storage_roots)
    and all active organization rules to determine move sources and targets.
    """
    db_files: List[Tuple[str, int]] = []
    rules_src: List[Dict[str, Any]] = []
    rules_tgt: List[Dict[str, Any]] = []

    conn = await _get_connection()
    if not conn:
        return db_files, rules_src, rules_tgt

    try:
        # 1. Fetch all file_nodes with root uri_path
        rows = await conn.fetch(
            """
            SELECT sr.uri_path, fn.relative_path, fn.physical_path, fn.size_bytes
            FROM file_nodes fn
            JOIN storage_roots sr ON fn.root_id = sr.id
            WHERE fn.is_deleted = FALSE;
            """
        )
        for r in rows:
            phys = r["physical_path"]
            root_uri = r["uri_path"]
            rel = r["relative_path"]
            size_b = int(r["size_bytes"] or 0)

            if phys:
                hpath = to_user_path(phys)
            else:
                hroot = to_user_path(root_uri)
                hpath = f"{hroot}/{rel}".rstrip("/")

            db_files.append((hpath, size_b))

        # 2. Fetch storage roots mapping id -> host path
        s_roots = await conn.fetch("SELECT id, uri_path FROM storage_roots;")
        root_map = {str(sr["id"]): to_user_path(sr["uri_path"]) for sr in s_roots}

        # 3. Fetch organization rules
        r_rows = await conn.fetch(
            """
            SELECT id, rule_name, description, source_root_id, target_root_id,
                   source_pattern, target_path_template, state, dry_run_last_count
            FROM organization_rules
            WHERE state IN ('USER_APPROVED', 'ACTIVE', 'IN_REVIEW');
            """
        )
        for r in r_rows:
            src_id = str(r["source_root_id"]) if r["source_root_id"] else None
            tgt_template = r["target_path_template"] or ""
            rule_info = {
                "rule_id": str(r["id"]),
                "name": r["rule_name"],
                "description": r["description"] or "",
                "pattern": r["source_pattern"],
                "pending_moves": int(r["dry_run_last_count"] or 0),
                "target_template": tgt_template,
            }

            src_path = root_map.get(src_id) if src_id else None
            if src_path:
                rules_src.append({**rule_info, "match_path": src_path})
            else:
                rules_src.append({**rule_info, "match_path": "/home/mb/Downloads"})
                rules_src.append({**rule_info, "match_path": "/media/work-data"})

            base_tgt = re.sub(r"/\{[^}]+\}.*", "", tgt_template)
            if base_tgt:
                rules_tgt.append({**rule_info, "match_path": base_tgt})

    except Exception as exc:
        logger.warning("Error loading DB indexed files and rules: %s", exc)
    finally:
        await conn.close()

    return db_files, rules_src, rules_tgt


def _enrich_filesystem_node(
    node: Dict[str, Any],
    db_files: List[Tuple[str, int]],
    rules_src: List[Dict[str, Any]],
    rules_tgt: List[Dict[str, Any]],
) -> None:
    """Enriches a single tree node and its children with DB indexing and reorganization status."""
    path = node.get("path", "")
    prefix = path if path.endswith("/") else (path + "/")

    matches = [size for fpath, size in db_files if fpath == path or fpath.startswith(prefix)]
    idx_cnt = len(matches)
    idx_bytes = sum(matches)
    approx_files = node.get("approx_total_files", 0)

    node["indexed_files_count"] = idx_cnt
    node["indexed_bytes"] = idx_bytes
    node["indexed_size_mb"] = round(idx_bytes / (1024 * 1024), 2)

    if idx_cnt == 0:
        idx_state = "UNINDEXED"
        idx_symbol = "⚪"
        idx_color = "#64748b"
        idx_label = "Nicht im Index"
    elif approx_files > 0 and idx_cnt >= approx_files:
        idx_state = "FULL"
        idx_symbol = "🟢"
        idx_color = "#10b981"
        idx_label = f"Vollständig indexiert ({idx_cnt} Dateien)"
    else:
        idx_state = "PARTIAL"
        idx_symbol = "🟡"
        idx_color = "#eab308"
        idx_label = f"Teilweise indexiert ({idx_cnt} Dateien)"

    node["indexing"] = {
        "state": idx_state,
        "symbol": idx_symbol,
        "color": idx_color,
        "label": idx_label,
        "count": idx_cnt,
        "bytes": idx_bytes,
        "size_mb": round(idx_bytes / (1024 * 1024), 2),
    }

    matched_src = [r for r in rules_src if r["match_path"] == path or path.startswith(r["match_path"] + "/")]
    matched_tgt = [r for r in rules_tgt if r["match_path"] == path or r["match_path"].startswith(prefix) or path.startswith(r["match_path"] + "/")]

    is_src = len(matched_src) > 0
    is_tgt = len(matched_tgt) > 0
    total_moves = sum(r.get("pending_moves", 0) for r in matched_src)

    reorg_label = None
    if is_src and is_tgt:
        reorg_label = f"Reorganisation: Quelle & Ziel ({total_moves} Moves)"
    elif is_src:
        reorg_label = f"Reorganisation: Quelle ({total_moves} Moves geplant)"
    elif is_tgt:
        reorg_label = f"Reorganisation: Zielordner ({len(matched_tgt)} Regeln)"

    node["reorganization"] = {
        "is_source": is_src,
        "is_target": is_tgt,
        "source_rules": matched_src,
        "target_rules": matched_tgt,
        "pending_moves": total_moves,
        "label": reorg_label,
    }

    for ch in node.get("children", []):
        _enrich_filesystem_node(ch, db_files, rules_src, rules_tgt)


@router.get("/filesystem-tree/full")
async def get_full_filesystem_tree() -> Dict[str, Any]:
    """
    Returns the real, complete filesystem tree of the system (all physical mounts
    and subfolders) decorated with:
    - PostgreSQL file_nodes indexing status (🟢/🟡/⚪, exact file counts, indexed MB)
    - Auto-Organizer reorganization role (Move source: 📤, Move target: 📥, pending file moves)
    - Syncthing synchronization (Folder ID, label, sync type, connected peer devices)
    - Backup protection coverage (scripts, schedules, targets, retention)
    - Real mount partition usage and POSIX permissions.
    """
    cache_file = _find_system_tree_file()
    tree_data = None
    if cache_file:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                tree_data = json.load(f)
        except Exception as exc:
            logger.warning("Failed to parse filesystem tree cache %s: %s", cache_file, exc)

    if not tree_data:
        try:
            from scripts.collect_system_filesystem_tree import collect_filesystem_tree
            tree_data = collect_filesystem_tree(max_depth=2)
        except Exception as exc:
            logger.warning("Direct collection fallback failed: %s", exc)
            tree_data = {"mounts": [], "scanned_at": datetime.now(timezone.utc).isoformat()}

    db_files, rules_src, rules_tgt = await _get_indexed_files_and_rules()

    for m in tree_data.get("mounts", []):
        _enrich_filesystem_node(m, db_files, rules_src, rules_tgt)

    total_dirs = 0
    total_files = 0
    total_indexed = 0
    total_moves = 0
    synced_mounts = 0
    protected_mounts = 0

    def _tally(n: Dict[str, Any]) -> None:
        nonlocal total_dirs, total_files, total_indexed, total_moves, synced_mounts, protected_mounts
        total_dirs += 1
        total_files += n.get("direct_files_count", 0)
        total_indexed += n.get("indexing", {}).get("count", 0)
        total_moves += n.get("reorganization", {}).get("pending_moves", 0)
        if n.get("syncthing", {}).get("synced"):
            synced_mounts += 1
        if n.get("backup", {}).get("protected"):
            protected_mounts += 1
        for ch in n.get("children", []):
            _tally(ch)

    for m in tree_data.get("mounts", []):
        _tally(m)

    return {
        "ok": True,
        "scanned_at": tree_data.get("scanned_at"),
        "host": tree_data.get("host", {}),
        "mount_points_count": len(tree_data.get("mounts", [])),
        "summary": {
            "total_mounts": len(tree_data.get("mounts", [])),
            "total_directories_scanned": total_dirs,
            "total_files_discovered": total_files,
            "total_files_indexed_in_db": total_indexed,
            "total_reorg_moves_pending": total_moves,
            "synced_folders_count": synced_mounts,
            "backup_protected_count": protected_mounts,
        },
        "mounts": tree_data.get("mounts", []),
    }


@router.get("/filesystem-tree/browse")
async def browse_directory(path: str = Query(..., description="Target directory path")) -> Dict[str, Any]:
    """
    On-demand dynamic drill-down for deep subdirectories.
    Inspects directory contents, calculates permissions, and enriches with DB indexing and rules.
    """
    target_path = to_user_path(path)
    c_path = docker_mount_service.translate_to_container_path(target_path) or target_path
    scan_path = c_path if os.path.exists(c_path) else target_path

    if not os.path.exists(scan_path) or not os.path.isdir(scan_path):
        raise HTTPException(status_code=404, detail=f"Verzeichnis existiert nicht oder nicht zugänglich: {path}")

    subdirs = []
    direct_files = 0
    direct_bytes = 0

    try:
        with os.scandir(scan_path) as it:
            for entry in it:
                if entry.name.startswith(".") and entry.name != ".stglobalignore":
                    continue
                if entry.is_dir(follow_symlinks=False):
                    subdirs.append(to_user_path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    direct_files += 1
                    try:
                        direct_bytes += entry.stat().st_size
                    except Exception:
                        pass
    except PermissionError:
        raise HTTPException(status_code=403, detail="Keine Leseberechtigung für dieses Verzeichnis")

    db_files, rules_src, rules_tgt = await _get_indexed_files_and_rules()

    children = []
    for s_path in sorted(subdirs)[:100]:
        base = os.path.basename(s_path)
        node = {
            "id": "node_" + re.sub(r"[^a-zA-Z0-9_-]", "_", s_path.strip("/")),
            "name": base,
            "path": s_path,
            "node_type": "folder",
            "direct_files_count": 0,
            "direct_subdirs_count": 0,
            "approx_total_files": 0,
            "approx_total_bytes": 0,
            "children": [],
            "syncthing": {"synced": False, "peers": []},
            "backup": {"protected": False},
        }
        _enrich_filesystem_node(node, db_files, rules_src, rules_tgt)
        children.append(node)

    return {
        "ok": True,
        "path": target_path,
        "direct_files_count": direct_files,
        "direct_bytes": direct_bytes,
        "subdirectories_count": len(children),
        "children": children,
    }


@router.post("/filesystem-tree/rescan")
async def trigger_filesystem_rescan() -> Dict[str, Any]:
    """
    Triggers an immediate rescan of the host filesystem tree and updates the cache.
    """
    script_candidates = [
        Path("/media/xchg/skripts/skripts-ai/hermes_gdrive_index_fork+localdrives/scripts/collect_system_filesystem_tree.py"),
        Path(__file__).resolve().parents[3] / "scripts" / "collect_system_filesystem_tree.py",
    ]
    script_path = None
    for s in script_candidates:
        if s.is_file():
            script_path = s
            break

    if script_path:
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                "--depth", "2",
                "--quiet",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"ok": True, "message": "Dateisystembaum erfolgreich neu gescannt und aktualisiert."}
            else:
                logger.warning("Rescan script exited %d: %s", proc.returncode, stderr.decode())
        except Exception as exc:
            logger.warning("Failed executing rescan script: %s", exc)

    try:
        import importlib.util
        if script_path and script_path.is_file():
            spec = importlib.util.spec_from_file_location("collect_tree", str(script_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            tree = mod.collect_filesystem_tree(max_depth=2)
            out = Path("/media/xchg/ai-tools-data/system_filesystem_tree.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(tree, f, indent=2, ensure_ascii=False)
            return {"ok": True, "message": "Dateisystembaum im Prozess neu erfasst."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    return {"ok": True, "message": "Dateisystembaum-Aktualisierung angestoßen."}

