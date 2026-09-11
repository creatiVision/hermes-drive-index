"""
Hermes Auto-Organizer Dashboard Plugin API.

FastAPI router (15 routes) mounted at /api/plugins/auto-organizer/.
PostgreSQL-backed state persistence for plugin_state, taxonomy_nodes,
organization_rules, and execution_log.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, Dict, Iterator, List, Optional
from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from hermes_auto_organizer.config import DatabaseConfig
from hermes_auto_organizer.domain.models import (
    FileNode,
    MoveIntent,
    OperationType,
    OrganizationRule,
    RollbackState,
    RuleState,
    StorageRoot,
    StorageRootType,
    WatchMode,
)
from hermes_auto_organizer.domain.rule_engine import evaluate_modular_rule, resolve_destination_path
from hermes_auto_organizer.infrastructure.db.connection import DatabaseConnectionPool
from hermes_auto_organizer.infrastructure.db.repositories import (
    PostgresExecutionLedger,
    PostgresNodeRepository,
    PostgresRuleRepository,
)
from hermes_auto_organizer.infrastructure.storage.atomic_runner import AtomicExecutionRunner
from hermes_auto_organizer.infrastructure.storage.docker_mounts import (
    _is_safe_subpath,
    docker_mount_service,
)
from hermes_auto_organizer.infrastructure.storage.local_scanner import LocalFilesystemScanner
from hermes_auto_organizer.application.use_cases.dry_run import DryRunEngine

logger = logging.getLogger("hermes.plugins.auto_organizer")
router = APIRouter()

_DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"


# ── Database pool (singleton) ────────────────────────────────────────────────


_db_pool: Optional[DatabaseConnectionPool] = None
_pool_lock: Optional[Any] = None  # set lazily on first use


def _ensure_lock() -> Any:
    global _pool_lock
    if _pool_lock is None:
        import asyncio
        _pool_lock = asyncio.Lock()
    return _pool_lock


@asynccontextmanager
async def _get_conn_ctx() -> Iterator[Optional[asyncpg.Connection]]:
    """Async context manager yielding a raw connection from the shared pool.

    The connection is returned to the pool when the context exits. Routes use
    ``async with _get_conn_ctx() as conn:`` to avoid the 'connection has been
    released back to the pool' error that happens when acquiring is done in a
    helper and the caller holds a stale reference.
    """
    global _db_pool
    try:
        if _db_pool is None:
            lock = _ensure_lock()
            async with lock:
                if _db_pool is None:
                    cfg = DatabaseConfig()
                    pool = DatabaseConnectionPool(cfg)
                    await pool.initialize()
                    _db_pool = pool
        async with _db_pool.acquire() as conn:
            yield conn
    except Exception as exc:
        logger.warning("DB pool connection failed: %s", exc)
        yield None


async def _get_connection() -> Optional[asyncpg.Connection]:
    """Acquire a raw connection from the shared pool.

    Returns a live connection that the caller must release via ``await conn.close()``.
    This avoids the 'connection has been released back to the pool' error caused by
    acquiring inside a helper that exits its own context.
    """
    global _db_pool
    try:
        if _db_pool is None:
            lock = _ensure_lock()
            async with lock:
                if _db_pool is None:
                    cfg = DatabaseConfig()
                    _db_pool = DatabaseConnectionPool(cfg)
                    await _db_pool.initialize()
        if _db_pool is None:
            return None
        return await _db_pool.acquire_raw()
    except Exception as exc:
        logger.warning("DB pool connection failed: %s", exc)
        return None


_TREE_FILE = "/media/xchg/ai-tools-data/system_filesystem_tree.json"


def _find_system_tree_file() -> Path:
    """Resolve the host filesystem tree JSON path (overridable in tests)."""
    return Path(_TREE_FILE)


# ── Plugin-state helpers (plugin_state table) ────────────────────────────────


async def _get_state(conn: asyncpg.Connection, key: str) -> Optional[Dict[str, Any]]:
    row = await conn.fetchrow(
        "SELECT value FROM plugin_state WHERE key = $1;", key
    )
    if row is None:
        return None
    val = row["value"]
    return json.loads(val) if isinstance(val, str) else val


async def _set_state(conn: asyncpg.Connection, key: str, value: Any) -> None:
    await conn.execute(
        """
        INSERT INTO plugin_state (key, value) VALUES ($1, $2)
        ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW();
        """,
        key,
        json.dumps(value),
    )


# ── Schema models ────────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    roots: List[str] = Field(default_factory=list)


class TaxonomyNodeRequest(BaseModel):
    id: Optional[str] = None
    parent_id: Optional[str] = None
    node_name: str = ""
    node_path: str = ""
    icon: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    state: Optional[str] = None
    source: Optional[str] = None


class RuleCreateRequest(BaseModel):
    rule_name: str = ""
    description: Optional[str] = None
    source_pattern: str = "*"
    condition_json: Dict[str, Any] = Field(default_factory=dict)
    target_path_template: str = ""
    state: Optional[str] = None
    source: Optional[str] = None


class RuleChatRequest(BaseModel):
    message: str = ""


class PreviewRequest(BaseModel):
    rule_ids: Optional[List[str]] = None


class ExecuteRequest(BaseModel):
    batch_id: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _default_taxonomy_nodes() -> List[Dict[str, Any]]:
    return [
        {
            "id": "finanzen-steuern",
            "parent_id": None,
            "node_name": "10_PrivatBüro / Steuern & Finanzen",
            "node_path": "/media/privat-data/10_PrivatBüro/Steuern/{year}/",
            "icon": "📊",
            "description": "Eingehende Rechnungen, Quittungen, Bankbelege und Steuerunterlagen",
            "keywords": ["Rechnung", "Steuer", "Finanzamt", "Beleg", "Invoice"],
            "confidence": 0.98,
            "state": "USER_APPROVED",
            "source": "synthesized",
        },
        {
            "id": "finanzen-ausgangsrechnungen",
            "parent_id": None,
            "node_name": "001_cv-bookaccount / Ausgangsrechnungen",
            "node_path": "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen/",
            "icon": "📤",
            "description": "Ausgehende Honorar- und Projektrechnungen",
            "keywords": ["Rechnung", "Honorar", "USt-IdNr", "Invoice"],
            "confidence": 0.99,
            "state": "USER_APPROVED",
            "source": "synthesized",
        },
        {
            "id": "finanzen-eingangsrechnungen",
            "parent_id": None,
            "node_name": "001_cv-bookaccount / Eingangsrechnungen",
            "node_path": "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
            "icon": "📥",
            "description": "Lieferantenrechnungen, SaaS-Tools und Betriebsausgaben",
            "keywords": ["Eingangsrechnung", "Vorsteuer", "Hetzner", "OpenAI"],
            "confidence": 0.98,
            "state": "USER_APPROVED",
            "source": "synthesized",
        },
        {
            "id": "work-kundenprojekte",
            "parent_id": None,
            "node_name": "002_cv-projects / Kunden & Webdesign",
            "node_path": "/media/work-data/002_cv-projects/{project_name}/",
            "icon": "🚀",
            "description": "Kunden-Websites, Themes, UI-Assets und Repositories",
            "keywords": ["Projekt", "Webdesign", "WordPress", "Repo"],
            "confidence": 0.95,
            "state": "USER_APPROVED",
            "source": "synthesized",
        },
        {
            "id": "work-ai-agents",
            "parent_id": None,
            "node_name": "KI-Agent-Skills",
            "node_path": "/media/xchg/ai-agents-workspaces/skills/",
            "icon": "🤖",
            "description": "Hermes-, Jules- und LangChain-Skills, Prompts und MCP-Konfigurationen",
            "keywords": ["Skill", "Agent", "Hermes", "MCP"],
            "confidence": 0.99,
            "state": "USER_APPROVED",
            "source": "synthesized",
        },
        {
            "id": "dumpzone-cleanup",
            "parent_id": None,
            "node_name": "Downloads Dumpzone",
            "node_path": "trash://",
            "icon": "🧹",
            "description": "Temporäre Dateien, Installer und Duplikate in den Papierkorb",
            "keywords": ["installer", "setup", "tmp", "Duplikat"],
            "confidence": 0.95,
            "state": "USER_APPROVED",
            "source": "synthesized",
        },
    ]


def _build_rule_thought_process(rule: OrganizationRule) -> Dict[str, Any]:
    """Derive a concise thought-process dict from a rule's stored fields."""
    cond = rule.condition_json or {}
    match_mode = cond.get("match_mode", "all")
    conditions = cond.get("conditions", [])
    return {
        "thinking": (
            f"Regel '{rule.rule_name}' (Zustand: {rule.state.value}) wurde mit "
            f"Match-Modus '{match_mode}' und {len(conditions)} Bedingung(en) erstellt. "
            f"Quellmuster: {rule.source_pattern}. Zielvorlage: {rule.target_path_template}."
        ),
        "evidence": cond,
        "llm": False,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  1 — GET /health
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    conn = await _get_connection()
    db_ok = False
    table_count = 0
    pgvector_ok = False
    if conn is not None:
        try:
            row = await conn.fetchrow(
                """
                SELECT count(*) AS c FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND (table_name LIKE 'file_%' OR table_name LIKE 'storage_%'
                       OR table_name LIKE 'organization_%' OR table_name LIKE 'plugin_%'
                       OR table_name LIKE 'taxonomy_%' OR table_name LIKE 'execution_%');
                """
            )
            table_count = int(row["c"]) if row else 0
            db_ok = True
            pgvector_ok = bool(os.getenv("HERMES_DB_PGVECTOR_AVAILABLE", "false").lower() == "true")
        except Exception:
            pass
    return {
        "ok": True,
        "plugin": "auto-organizer",
        "version": "1.0.0",
        "database_connected": db_ok,
        "pgvector_available": pgvector_ok,
        "table_count": table_count,
        "timestamp": os.times().elapsed if hasattr(os.times(), "elapsed") else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  2 — GET /stats
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        return {
            "total_files": 0, "total_size_mb": 0.0, "total_roots": 0,
            "open_anomalies": 0, "active_rules": 0, "recent_batches": 0,
            "db_connected": False,
        }
    try:
        f_row = await conn.fetchrow(
            "SELECT COUNT(*) AS count, COALESCE(SUM(size_bytes), 0) AS size FROM file_nodes WHERE NOT is_deleted;"
        )
        r_row = await conn.fetchrow("SELECT COUNT(*) AS count FROM storage_roots WHERE is_active;")
        a_row = await conn.fetchrow("SELECT COUNT(*) AS count FROM structural_anomalies WHERE status = 'open';")
        rule_row = await conn.fetchrow(
            "SELECT COUNT(*) AS count FROM organization_rules WHERE state = 'USER_APPROVED';"
        )
        b_row = await conn.fetchrow("SELECT COUNT(DISTINCT batch_id) AS count FROM execution_log;")
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
        await conn.close() if hasattr(conn, "close") else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  3 — GET /mounts
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/mounts")
async def list_mounts() -> Dict[str, Any]:
    mounts = docker_mount_service.get_mounts(force_refresh=True)
    writable = sum(1 for m in mounts if m.get("is_writable"))
    free_gb = round(sum(m.get("free_gb", 0) for m in mounts if m.get("is_writable")), 1)
    return {
        "ok": True,
        "in_container": docker_mount_service.is_in_container(),
        "total_mounts": len(mounts),
        "writable_mounts": writable,
        "total_free_gb": free_gb,
        "mounts": mounts,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  4 — GET /sources/tree
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/sources/tree")
async def get_source_tree(path: str = Query("/", description="Root path to browse")) -> Dict[str, Any]:
    tree_file = _find_system_tree_file()
    if tree_file is not None and tree_file.exists():
        try:
            raw = json.loads(tree_file.read_text(encoding="utf-8"))
            mounts = raw.get("mounts", [])
            # Navigate to requested path
            if path == "/":
                return {"ok": True, "path": "/", "node_type": "root", "children": mounts}
            # Walk down the tree
            parts = [p for p in path.split("/") if p]
            current: Any = None
            for m in mounts:
                if m.get("path", "") == ("/" + parts[0]) if parts else False:
                    current = m
                    break
            if current is None and parts:
                for m in mounts:
                    child = _find_child(m.get("children", []), parts[0])
                    if child:
                        current = child
                        break
            if current is None:
                return {"ok": False, "error": f"Path not found: {path}"}
            # Walk remaining parts
            for p in parts[1:]:
                children = current.get("children", [])
                nxt = _find_child(children, p)
                if nxt is None:
                    return {"ok": False, "error": f"Path not found: {path}"}
                current = nxt
            return {
                "ok": True,
                "path": path,
                "node_type": current.get("node_type", "folder"),
                "children": current.get("children", []),
                "is_symlink": current.get("is_symlink", False),
                "real_path": current.get("real_path"),
            }
        except Exception as exc:
            logger.warning("Failed to read tree file %s: %s", tree_file, exc)

    # Fallback: return mount roots only
    mounts = docker_mount_service.get_mounts(force_refresh=True)
    tree = [
        {
            "id": f"mnt_{m['host_path'].replace('/', '_').strip('_')[:40]}",
            "name": Path(m["host_path"]).name,
            "path": m["host_path"],
            "node_type": "mount",
            "mount_point": m["host_path"],
            "is_writable": m.get("is_writable", False),
            "children": [],
        }
        for m in mounts
    ]
    if path == "/":
        return {"ok": True, "path": "/", "node_type": "root", "children": tree}
    return {"ok": False, "error": f"Path not found: {path}"}


def _find_child(children: Any, name: str) -> Optional[Dict[str, Any]]:
    for c in children:
        if c.get("name") == name:
            return c
    return None


def _resolve_tree_path(mounts: List[Dict[str, Any]], path: str) -> Optional[Dict[str, Any]]:
    """Resolve a host path against the tree mounts, returning the matched node (or None)."""
    if path == "/":
        return {"node_type": "root", "children": mounts}
    parts = [p for p in path.split("/") if p]
    if not parts:
        return {"node_type": "root", "children": mounts}
    current: Any = None
    for m in mounts:
        if m.get("path", "") == ("/" + parts[0]):
            current = m
            break
    if current is None and parts:
        for m in mounts:
            child = _find_child(m.get("children", []), parts[0])
            if child:
                current = child
                break
    if current is None:
        return None
    for p in parts[1:]:
        children = current.get("children", [])
        nxt = _find_child(children, p)
        if nxt is None:
            return None
        current = nxt
    return current


def _walk_all(nodes: List[Dict[str, Any]], prefix: str, limit: int = 12) -> List[Dict[str, Any]]:
    """Collect descendant folder paths under a node set, filtered by a host-path prefix."""
    out: List[Dict[str, Any]] = []
    def rec(items: List[Dict[str, Any]]) -> None:
        for it in items or []:
            p = it.get("path") or ""
            if p.startswith(prefix):
                out.append({"path": p, "name": it.get("name") or Path(p).name})
            if len(out) < limit:
                rec(it.get("children", []))
    rec(nodes)
    return out[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  4b — GET /sources/complete (Autocomplete + Breadcrumb)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/sources/complete")
async def complete_source_path(prefix: str = Query("/", description="Partial path prefix to autocomplete")) -> Dict[str, Any]:
    tree_file = _find_system_tree_file()
    mounts: List[Dict[str, Any]] = []
    if tree_file is not None and tree_file.exists():
        try:
            raw = json.loads(tree_file.read_text(encoding="utf-8"))
            mounts = raw.get("mounts", [])
        except Exception as exc:
            logger.warning("Failed to read tree file for autocomplete: %s", exc)
    if not mounts:
        mounts = docker_mount_service.get_mounts(force_refresh=True)
        # DockerMountService returns flat dicts with host_path/label and no children.
        # Normalize to tree-node shape so filtering below works.
        mounts = [
            {
                "path": m.get("host_path") or m.get("path") or "",
                "name": m.get("label") or m.get("name") or m.get("host_path") or "",
                "node_type": "mount",
                "children": [],
            }
            for m in mounts
        ]

    # Determine the directory portion of the typed prefix: match children of the parent dir
    prefix = prefix or "/"
    base_dir = prefix
    if not prefix.endswith("/"):
        base_dir = prefix[: prefix.rfind("/")] or "/"
    elif prefix != "/":
        base_dir = prefix  # already a dir, list its children
    else:
        base_dir = "/"

    # Resolve the base node to list its children as suggestions
    base_node = _resolve_tree_path(mounts, base_dir)
    children: List[Dict[str, Any]] = base_node.get("children", []) if base_node else []
    suggestions: List[Dict[str, Any]] = []
    for c in children:
        cpath = c.get("path") or ""
        if cpath.startswith(prefix):
            suggestions.append({"path": cpath, "name": c.get("name") or Path(cpath).name})
    # Fallback: if nothing matches directly, do a preorder search for prefix under root
    if not suggestions and prefix:
        suggestions = _walk_all(mounts, prefix)

    # Breadcrumb segments for the current base directory
    crumbs: List[Dict[str, str]] = []
    if base_dir != "/":
        parts = [p for p in base_dir.split("/") if p]
        acc = ""
        for p in parts:
            acc += "/" + p
            crumbs.append({"label": p, "path": acc})

    return {
        "ok": True,
        "prefix": prefix,
        "base_dir": base_dir,
        "suggestions": suggestions,
        "crumbs": crumbs,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  5 — POST /sources/scan
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/sources/scan")
async def scan_sources(req: ScanRequest) -> Dict[str, Any]:
    if not req.roots:
        return {"ok": False, "error": "No roots provided"}

    scanned = 0
    errors: List[str] = []

    for root_path in req.roots:
        try:
            root = StorageRoot(
                root_name=Path(root_path).name or root_path,
                root_type=StorageRootType.LOCAL_DIR,
                uri_path=root_path,
                watch_mode=WatchMode.MANUAL,
                is_active=True,
            )
            repo = PostgresNodeRepository(_db_pool)
            persisted_root = await repo.upsert_root(root)
            scanner = LocalFilesystemScanner()
            batch: List[FileNode] = []
            async for node in scanner.scan_root(persisted_root, compute_sha256=False):
                batch.append(node)
                if len(batch) >= 500:
                    scanned += await repo.batch_upsert_nodes(batch)
                    batch.clear()
            if batch:
                scanned += await repo.batch_upsert_nodes(batch)
        except Exception as exc:
            logger.error("Scan root failed %s: %s", root_path, exc)
            errors.append(f"{root_path}: {exc}")

    return {
        "ok": True,
        "roots_scanned": len(req.roots),
        "files_indexed": scanned,
        "errors": errors,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  6 — GET /taxonomy
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/taxonomy")
async def get_taxonomy() -> Dict[str, Any]:
    conn = await _get_connection()
    nodes: List[Dict[str, Any]] = []

    if conn is not None:
        try:
            rows = await conn.fetch(
                """
                SELECT id, parent_id, node_name, node_path, icon, description,
                       keywords, confidence, state, source
                FROM taxonomy_nodes
                ORDER BY COALESCE(parent_id, '') ASC, node_name ASC;
                """
            )
            if rows:
                node_map: Dict[str, Dict[str, Any]] = {}
                for r in rows:
                    node_map[r["id"]] = {
                        "id": str(r["id"]),
                        "parent_id": str(r["parent_id"]) if r["parent_id"] else None,
                        "node_name": r["node_name"],
                        "node_path": r["node_path"],
                        "icon": r["icon"],
                        "description": r["description"],
                        "keywords": r["keywords"] or [],
                        "confidence": float(r["confidence"]) if r["confidence"] else None,
                        "state": r["state"],
                        "source": r["source"],
                        "children": [],
                    }
                roots: List[Dict[str, Any]] = []
                for n in node_map.values():
                    pid = n["parent_id"]
                    if pid and pid in node_map:
                        node_map[pid]["children"].append(n)
                    else:
                        roots.append(n)
                nodes = roots
        except Exception as exc:
            logger.warning("taxonomy_nodes query failed: %s", exc)

    if not nodes:
        # Fallback: load from plugin_state, then seed defaults
        if conn is not None:
            try:
                saved = await _get_state(conn, "taxonomy_tree")
                if saved:
                    nodes = saved
            except Exception:
                pass
        if not nodes:
            nodes = _default_taxonomy_nodes()
            if conn is not None:
                try:
                    await _set_state(conn, "taxonomy_tree", nodes)
                except Exception:
                    pass

    return {
        "ok": True,
        "total_nodes": len(nodes),
        "tree": nodes,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  7 — POST /taxonomy/node
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/taxonomy/node")
async def create_taxonomy_node(req: TaxonomyNodeRequest) -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        node_id = req.id or str(uuid4())
        await conn.execute(
            """
            INSERT INTO taxonomy_nodes (id, parent_id, node_name, node_path, icon,
                description, keywords, confidence, state, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO UPDATE SET
                node_name = EXCLUDED.node_name,
                node_path = EXCLUDED.node_path,
                icon = COALESCE(EXCLUDED.icon, taxonomy_nodes.icon),
                description = COALESCE(EXCLUDED.description, taxonomy_nodes.description),
                keywords = COALESCE(EXCLUDED.keywords, taxonomy_nodes.keywords),
                confidence = COALESCE(EXCLUDED.confidence, taxonomy_nodes.confidence),
                state = COALESCE(EXCLUDED.state, taxonomy_nodes.state),
                source = COALESCE(EXCLUDED.source, taxonomy_nodes.source),
                updated_at = NOW();
            """,
            UUID(node_id) if len(node_id) == 36 else node_id,
            UUID(req.parent_id) if req.parent_id and len(req.parent_id) == 36 else req.parent_id,
            req.node_name,
            req.node_path,
            req.icon,
            req.description,
            json.dumps(req.keywords),
            req.confidence,
            req.state or "USER_APPROVED",
            req.source or "manual",
        )
        row = await conn.fetchrow(
            "SELECT id, parent_id, node_name, node_path, icon, description, keywords, confidence, state, source FROM taxonomy_nodes WHERE id = $1;",
            UUID(node_id) if len(node_id) == 36 else node_id,
        )
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve created node")

        node = {
            "id": str(row["id"]),
            "parent_id": str(row["parent_id"]) if row["parent_id"] else None,
            "node_name": row["node_name"],
            "node_path": row["node_path"],
            "icon": row["icon"],
            "description": row["description"],
            "keywords": row["keywords"] if isinstance(row["keywords"], list) else (json.loads(row["keywords"]) if isinstance(row["keywords"], str) else []),
            "confidence": float(row["confidence"]) if row["confidence"] else None,
            "state": row["state"],
            "source": row["source"],
        }
        children = await conn.fetch(
            "SELECT id, node_name FROM taxonomy_nodes WHERE parent_id = $1;",
            UUID(node_id) if len(node_id) == 36 else node_id,
        )
        node["children"] = [{"id": str(c["id"]), "node_name": c["node_name"]} for c in children]
        return {"ok": True, "node": node}
    finally:
        await conn.close() if hasattr(conn, "close") else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  8 — GET /rules
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/rules")
async def list_rules() -> Dict[str, Any]:
    conn = await _get_connection()
    adopted: List[Dict[str, Any]] = []
    suggested: List[Dict[str, Any]] = []

    if conn is not None:
        try:
            rows = await conn.fetch(
                """SELECT id, rule_name, description, source_pattern,
                          condition_json, target_path_template, state,
                          dry_run_last_count, created_at, updated_at
                   FROM organization_rules ORDER BY created_at DESC;"""
            )
            adopted = [
                {
                    "id": str(r["id"]),
                    "rule_name": r["rule_name"],
                    "description": r["description"],
                    "source_pattern": r["source_pattern"],
                    "condition_json": r["condition_json"] if isinstance(r["condition_json"], dict) else json.loads(r["condition_json"]),
                    "target_path_template": r["target_path_template"],
                    "state": r["state"],
                    "thought_process": "Regel basiert auf Dateimustern und Schlüsselworterkennung.",
                    "source": "user",
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning("list_rules DB failed: %s", exc)

    # AI-suggested rules (static set until pipeline is wired)
    suggested = [
        {
            "id": "ai_rechnungen",
            "rule_name": "Finanzrechnungen archivieren",
            "description": "PDF-Rechnungen mit Steuernummer/Betrag nach Jahr archivieren",
            "source_pattern": "*",
            "condition_json": {
                "match_mode": "all",
                "conditions": [
                    {"field": "extension", "operator": "in", "value": ["pdf"]},
                    {"field": "keyword", "operator": "contains", "value": "Rechnung"},
                ],
            },
            "target_path_template": "/media/privat-data/10_PrivatBüro/Steuern/{year}/",
            "state": "USER_APPROVED",
            "created_at": None,
            "thought_process": {
                "thinking": "PDF-Rechnungen wurden im Downloads-Ordner erkannt. Regel schlägt Archivierung nach Jahr vor.",
                "evidence": {"sample_files": ["Rechnung_2025.pdf", "Steuerbescheid_2024.pdf"]},
                "llm": False,
            },
            "source": "ai",
        },
        {
            "id": "ai_contracts",
            "rule_name": "Verträge zentral ablegen",
            "description": "Vertrags-PDFs (.pdf, .docx) mit Vertrags-Keywords konsolidieren",
            "source_pattern": "*",
            "condition_json": {
                "match_mode": "all",
                "conditions": [
                    {"field": "extension", "operator": "in", "value": ["pdf", "docx"]},
                    {"field": "keyword", "operator": "contains", "value": "Vertrag"},
                ],
            },
            "target_path_template": "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/",
            "state": "USER_APPROVED",
            "created_at": None,
            "thought_process": {
                "thinking": "Mehrere Vertrags-PDFs identifiziert. Regel schlägt zentrale Ablage vor.",
                "evidence": {"sample_files": ["Handwerkervertrag.pdf", "Mietvertrag.docx"]},
                "llm": False,
            },
            "source": "ai",
        },
    ]

    return {
        "ok": True,
        "total": len(adopted) + len(suggested),
        "adopted": adopted,
        "suggested": suggested,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route  9 — POST /rules
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/rules")
async def create_or_update_rule(req: RuleCreateRequest) -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        state = req.state or "USER_APPROVED"
        source = req.source or "user"

        # Check if a rule with this name already exists
        existing = await conn.fetchrow(
            "SELECT id, state FROM organization_rules WHERE rule_name = $1;", req.rule_name
        )

        if existing:
            rule_id = existing["id"]
            await conn.execute(
                """
                UPDATE organization_rules SET
                    description = COALESCE($1, description),
                    source_pattern = $2,
                    condition_json = $3::jsonb,
                    target_path_template = $4,
                    state = $5,
                    source = $6,
                    updated_at = NOW()
                WHERE id = $7;
                """,
                req.description,
                req.source_pattern,
                json.dumps(req.condition_json),
                req.target_path_template,
                state,
                source,
                rule_id,
            )
        else:
            rule_id = uuid4()
            await conn.execute(
                """
                INSERT INTO organization_rules (
                    id, rule_name, description, source_pattern,
                    condition_json, target_path_template, state, source
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                """,
                rule_id,
                req.rule_name,
                req.description,
                req.source_pattern,
                json.dumps(req.condition_json),
                req.target_path_template,
                state,
                source,
            )

        row = await conn.fetchrow(
            """
            SELECT id, rule_name, description, source_pattern, condition_json,
                   target_path_template, state, source, created_at, updated_at
            FROM organization_rules WHERE id = $1;
            """,
            rule_id,
        )
        if row is None:
            raise HTTPException(status_code=500, detail="Rule not found after save")

        cond = row["condition_json"]
        if isinstance(cond, str):
            cond = json.loads(cond)

        return {
            "ok": True,
            "rule_id": str(row["id"]),
            "rule_name": row["rule_name"],
            "description": row["description"],
            "source_pattern": row["source_pattern"],
            "condition_json": cond or {},
            "target_path_template": row["target_path_template"],
            "state": row["state"],
            "source": row["source"],
        }
    finally:
        await conn.close() if hasattr(conn, "close") else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 10 — POST /rules/{rule_id}/chat
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/rules/{rule_id}/chat")
async def rule_chat(rule_id: str, req: RuleChatRequest) -> Dict[str, Any]:
    conn = await _get_connection()
    rule_row = None
    if conn is not None:
        try:
            rule_row = await conn.fetchrow(
                "SELECT * FROM organization_rules WHERE id = $1 OR rule_name = $1;",
                rule_id,
            )
        except Exception:
            pass

    if rule_row is None:
        # Check _CHAT_MODIFIED_RULES fallback for in-memory state
        if rule_id in _CHAT_MODIFIED_RULES:
            rule_row = _CHAT_MODIFIED_RULES[rule_id]
        else:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    # Build rule snippet
    if isinstance(rule_row, dict):
        snippet = {
            "rule_name": rule_row.get("rule_name", rule_id),
            "description": rule_row.get("description"),
            "source_pattern": rule_row.get("source_pattern", "*"),
            "condition_json": rule_row.get("condition_json", {}),
            "target_path_template": rule_row.get("target_path_template", ""),
            "state": rule_row.get("state", "USER_APPROVED"),
        }
        if isinstance(snippet["condition_json"], str):
            try:
                snippet["condition_json"] = json.loads(snippet["condition_json"])
            except Exception:
                snippet["condition_json"] = {}
    else:
        snippet = {
            "rule_name": rule_row.rule_name,
            "description": rule_row.description,
            "source_pattern": rule_row.source_pattern,
            "condition_json": rule_row.condition_json,
            "target_path_template": rule_row.target_path_template,
            "state": rule_row.state.value,
        }

    system_prompt = (
        "Du bist der Regel-Experte des Hermes Auto-Organizer-Plugins. "
        "Erkläre kurz und präzise (3-5 Sätze), warum die folgende Organisationsregel existiert, "
        "und beantworte dann die Anfrage des Nutzers zur Modifikation der Regel. "
        "Gib das Ergebnis als JSON-Objekt mit den Feldern "
        "\"thought_process\" (string), \"response\" (string), "
        "\"modified_condition\" (object|null) und \"modified_target\" (string|null) zurück.\n\n"
        "Regel im Kontext:\n" + json.dumps(snippet, ensure_ascii=False)
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": req.message})

    thought_process, modified_condition, modified_target = _llm_chat_result(messages)

    # Save to plugin_state
    if conn is not None:
        try:
            await _set_state(
                conn,
                f"rule_chat_{rule_id}",
                {
                    "last_message": req.message,
                    "thought_process": thought_process,
                    "modified_condition": modified_condition,
                    "modified_target": modified_target,
                    "timestamp": os.environ.get("HERMES_BUILD_DATE", __import__("datetime").datetime.now().isoformat()),
                },
            )
        except Exception as exc:
            logger.warning("Failed to persist rule_chat state: %s", exc)
        finally:
            await conn.close() if hasattr(conn, "close") else None

    return {
        "ok": True,
        "rule_id": rule_id,
        "thought_process": thought_process,
        "modified_condition": modified_condition,
        "modified_target": modified_target,
    }


# ── LLM chat helper ──────────────────────────────────────────────────────────


async def _llm_chat_result(
    messages: List[Dict[str, str]],
) -> tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    """Call OpenAI-compatible chat completions; return (thought, condition, target)."""
    base_url = os.getenv("HERMES_CHAT_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1"
    api_key = os.getenv("HERMES_CHAT_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    model = os.getenv("HERMES_CHAT_MODEL") or os.getenv("OPENAI_MODEL") or _DEFAULT_MODEL

    if not api_key:
        return (
            "Kein LLM konfiguriert — Rule-Engine-Auswertung: "
            f"condition={json.dumps(messages[-1].get('content', ''), ensure_ascii=False)}",
            None,
            None,
        )

    try:
        import httpx
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code != 200:
            return (
                f"LLM-Response fehlgeschlagen (HTTP {resp.status_code})",
                None,
                None,
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return (
            parsed.get("thought_process") or parsed.get("thinking") or content[:500],
            parsed.get("modified_condition"),
            parsed.get("modified_target"),
        )
    except Exception as exc:
        logger.warning("LLM chat failed: %s", exc)
        return (
            f"LLM nicht verfügbar: {exc}. Rule-Engine-Auswertung verwendet.",
            None,
            None,
        )


# In-memory fallback store for chat-modified rules (backward-compat)


_CHAT_MODIFIED_RULES: Dict[str, Dict[str, Any]] = {}


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 11 — POST /rules/{rule_id}/toggle
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str) -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        uuid_id = UUID(rule_id)
        current = await conn.fetchrow(
            "SELECT state FROM organization_rules WHERE id = $1;", uuid_id
        )
        if current is None:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

        current_state = current["state"]
        new_state = "DISABLED" if current_state == "USER_APPROVED" else "USER_APPROVED"

        await conn.execute(
            "UPDATE organization_rules SET state = $1, updated_at = NOW() WHERE id = $2;",
            new_state,
            uuid_id,
        )
        return {"ok": True, "rule_id": rule_id, "state": new_state}
    finally:
        await conn.close() if hasattr(conn, "close") else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 12 — POST /preview
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/preview")
async def preview_dry_run(req: PreviewRequest) -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    batch_id = f"dry_{uuid4().hex[:12]}"
    try:
        # Fetch rules (filter by rule_ids if provided)
        if req.rule_ids:
            placeholders = ",".join(f"${i+1}" for i in range(len(req.rule_ids)))
            rules_rows = await conn.fetch(
                f"SELECT * FROM organization_rules WHERE id = ANY(ARRAY[{placeholders}]::uuid[]) AND state = 'USER_APPROVED';",
                *req.rule_ids,
            )
        else:
            rules_rows = await conn.fetch(
                "SELECT * FROM organization_rules WHERE state = 'USER_APPROVED';"
            )

        rules: List[OrganizationRule] = []
        for rr in rules_rows:
            cond = rr["condition_json"]
            if isinstance(cond, str):
                try:
                    cond = json.loads(cond)
                except Exception:
                    cond = {}
            rules.append(OrganizationRule(
                id=rr["id"],
                rule_name=rr["rule_name"],
                source_pattern=rr["source_pattern"],
                condition_json=cond or {},
                target_path_template=rr["target_path_template"],
                state=RuleState(rr["state"]),
            ))

        actions: List[Dict[str, Any]] = []
        seen_dest: set[str] = set()
        collisions = 0
        blocked = 0

        if not rules:
            result = {
                "batch_id": batch_id,
                "actions": [],
                "summary": {"total": 0, "valid": 0, "collisions": 0, "blocked": 0},
            }
        else:
            # Fetch candidate file nodes
            nodes_rows = await conn.fetch(
                """
                SELECT id, root_id, relative_path, physical_path, file_name,
                       size_bytes, mtime, file_extension, content_sha256
                FROM file_nodes
                WHERE NOT is_deleted
                ORDER BY mtime DESC
                LIMIT 500;
                """
            )
            nodes: List[FileNode] = [
                FileNode(
                    id=r["id"], root_id=r["root_id"], relative_path=r["relative_path"],
                    physical_path=r["physical_path"], file_name=r["file_name"],
                    size_bytes=r["size_bytes"], mtime=r["mtime"],
                    file_extension=r["file_extension"], content_sha256=r["content_sha256"],
                )
                for r in nodes_rows
            ]

            # Resolve a target root for DryRunEngine (first active root, or synthetic)
            roots = await conn.fetch("SELECT * FROM storage_roots WHERE is_active LIMIT 1;")
            target_root = StorageRoot(
                id=roots[0]["id"] if roots else uuid4(),
                root_name=roots[0]["root_name"] if roots else "default",
                root_type=StorageRootType.LOCAL_DIR,
                uri_path=roots[0]["uri_path"] if roots else "/",
                watch_mode=WatchMode.MANUAL,
                is_active=True,
            ) if roots else StorageRoot(
                id=uuid4(), root_name="default", root_type=StorageRootType.LOCAL_DIR,
                uri_path="/", watch_mode=WatchMode.MANUAL, is_active=True,
            )

            for rule in rules:
                intents = DryRunEngine.simulate_rule(rule, nodes, target_root)
                for intent in intents:
                    dest = intent.destination_path
                    has_collision = dest in seen_dest or Path(dest).exists()
                    if has_collision:
                        collisions += 1
                    seen_dest.add(dest)

                    m_check = docker_mount_service.validate_destination_path(dest)
                    is_blocked = (has_collision or not m_check["valid"])

                    if is_blocked:
                        blocked += 1

                    actions.append({
                        "file_name": Path(intent.source_path).name,
                        "source_path": intent.source_path,
                        "destination_path": dest,
                        "status": "collision" if has_collision else ("blocked" if not m_check["valid"] else "ok"),
                        "rule_name": rule.rule_name,
                    })

            summary = {
                "total": len(actions),
                "valid": len(actions) - collisions - blocked,
                "collisions": collisions,
                "blocked": blocked,
            }

            result = {
                "batch_id": batch_id,
                "actions": actions,
                "summary": summary,
            }

        # Persist to plugin_state
        if conn is not None:
            await _set_state(conn, "dry_run_result", result)

        return result
    finally:
        await conn.close() if hasattr(conn, "close") else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 13 — POST /execute
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/execute")
async def execute_batch(req: ExecuteRequest) -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # Read dry-run result from plugin_state
    dry_run = None
    try:
        dry_run = await _get_state(conn, "dry_run_result")
    except Exception:
        pass

    if dry_run is None:
        raise HTTPException(status_code=404, detail="No dry-run result found. Run /preview first.")

    actions = dry_run.get("actions", [])
    if not actions:
        return {"ok": True, "executed": 0, "message": "No actions to execute."}

    batch_id = req.batch_id or str(uuid4())
    batch_uuid = UUID(batch_id) if len(batch_id) == 36 else uuid4()
    executed = 0
    failed = 0

    ledger = PostgresExecutionLedger(_db_pool)
    for act in actions:
        if act.get("status") not in ("ok",):
            continue
        src = Path(act["source_path"])
        dst = Path(act["destination_path"])
        if not src.exists():
            failed += 1
            continue
        try:
            intent = MoveIntent(
                file_id=uuid4(),
                source_path=str(src),
                destination_path=str(dst),
                source_sha256=act.get("content_sha256", ""),
                operation_type=OperationType.LOCAL_MOVE,
                rule_id=UUID(act.get("rule_id", "00000000-0000-0000-0000-000000000000")),
            )
            record = AtomicExecutionRunner.execute_move(intent, batch_uuid)
            await ledger.append_record(record)
            executed += 1
        except Exception as exc:
            logger.error("Execute failed %s -> %s: %s", src, dst, exc)
            failed += 1

    return {
        "ok": True,
        "batch_id": batch_id,
        "executed": executed,
        "failed": failed,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 14 — GET /journal
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/journal")
async def get_journal() -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        return {"ok": True, "batches": []}

    try:
        rows = await conn.fetch(
            """
            SELECT batch_id,
                   MAX(executed_at) AS executed_at,
                   COUNT(*) AS file_count,
                   ARRAY_AGG(DISTINCT rule_id) AS rule_ids
            FROM execution_log
            GROUP BY batch_id
            ORDER BY MAX(executed_at) DESC;
            """
        )
        batches = [
            {
                "batch_id": str(r["batch_id"]),
                "executed_at": r["executed_at"].isoformat() if r["executed_at"] else None,
                "file_count": int(r["file_count"]),
                "rules": [str(x) for x in (r["rule_ids"] or []) if x],
                "status": "completed",
            }
            for r in rows
        ]
        return {"ok": True, "batches": batches}
    finally:
        await conn.close() if hasattr(conn, "close") else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 15 — POST /journal/{batch_id}/rollback
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/journal/{batch_id}/rollback")
async def rollback_batch(batch_id: str) -> Dict[str, Any]:
    conn = await _get_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        batch_uuid = UUID(batch_id) if len(batch_id) == 36 else UUID(batch_id.replace("-", ""))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid batch_id: {batch_id}")

    ledger = PostgresExecutionLedger(_db_pool)
    records = await ledger.list_batch_records(batch_uuid)
    records = [r for r in records if r.rollback_state.value == "EXECUTED"]

    if not records:
        return {"ok": False, "message": f"No executed records for batch {batch_id}"}

    reverted = 0
    for record in records:
        success = AtomicExecutionRunner.rollback_move(record)
        if success:
            await ledger.update_record_state(record.id, RollbackState.REVERTED)
            reverted += 1

    return {
        "ok": True,
        "batch_id": batch_id,
        "reverted_count": reverted,
        "total_records": len(records),
    }


# ── Re-exports for backward compatibility (tests) ────────────────────────────

# These aliases exist so existing test imports do not break immediately.
# They reference functions that are now route-handler closures above.
health_check = health_check
get_stats = get_stats
