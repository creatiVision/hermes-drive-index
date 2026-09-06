"""Public API.

Each entry point accepts an optional ``cfg`` (a resolved ``DriveIndexConfig``).
When omitted, ``default_config()`` is used, preserving the zero-argument
signatures the Hermes adapter relies on.
"""

from __future__ import annotations

from pathlib import Path

from .config import DriveIndexConfig, default_config
from .core.benchmark import benchmark_ocr_parameters as _benchmark_ocr_parameters
from .core.manifest import plan_incremental_actions
from .core.models import DriveFile
from .core.orchestrator import build_index as _build_index
from .core.orchestrator import incremental_update as _incremental_update
from .core.orchestrator import reindex_metadata_only as _reindex_metadata_only
from .core.orchestrator import search as _search
from .core.orchestrator import status as _status


def build_index(cfg: DriveIndexConfig | None = None) -> dict:
    return _build_index(cfg or default_config())


def incremental_update(cfg: DriveIndexConfig | None = None) -> dict:
    return _incremental_update(cfg or default_config())


def reindex_metadata_only(cfg: DriveIndexConfig | None = None) -> dict:
    return _reindex_metadata_only(cfg or default_config())


def benchmark_ocr_parameters(
    cfg: DriveIndexConfig | None = None,
    *,
    modes: list[str] | None = None,
    limit: int | None = None,
    golden_path: str | Path | None = None,
) -> dict:
    return _benchmark_ocr_parameters(
        cfg or default_config(),
        modes=modes,
        limit=limit,
        golden_path=Path(golden_path).expanduser() if golden_path else None,
    )
def search(query: str, top_k: int = 8, cfg: DriveIndexConfig | None = None) -> dict:
    return _search(cfg or default_config(), query=query, top_k=top_k)


def status(cfg: DriveIndexConfig | None = None) -> dict:
    return _status(cfg or default_config())


from .core.cleaner import (
    classify_old_files as _classify_old_files,
    detect_duplicates as _detect_duplicates,
    plan_document_structure as _plan_document_structure,
    plan_download_organization as _plan_download_organization,
)
from .core.local_index import index_local_directory as _index_local_directory
from .core.local_scanner import LocalFile, safe_trash, scan_local_directory
from .core.organizer_workflow import (
    OrganizerPlan,
    access_check,
    analyse_first,
    execute_on_approval,
    format_plan_presentation,
    intent_check,
    propose_plan,
    validate_approval,
)
from .core.sync import (
    SyncMapping,
    SyncPlan,
    apply_selective_sync,
    plan_selective_sync,
)


def find_duplicates(path: str | Path) -> dict:
    """Scan folder and detect exact duplicates, near-duplicates, and version variants."""
    p = Path(path).expanduser().resolve()
    files = scan_local_directory(p, recursive=True, compute_hashes=True)
    return _detect_duplicates(files)


def flag_old_files(path: str | Path, days_threshold: int = 90) -> dict:
    """Analyze folder by age and usage patterns into tiered inventory."""
    p = Path(path).expanduser().resolve()
    files = scan_local_directory(p, recursive=True, compute_hashes=False)
    return _classify_old_files(files, days_threshold=days_threshold)


def auto_organize_downloads(path: str | Path, by_date: bool = True) -> dict:
    """Plan sorting a flat downloads folder into subfolders by type and date."""
    return _plan_download_organization(Path(path).expanduser().resolve(), by_date=by_date)


def organize_documents(path: str | Path) -> dict:
    """Plan structured reorganization of a documents folder into 4-6 top-level categories."""
    return _plan_document_structure(Path(path).expanduser().resolve())


def index_local_folder(path: str | Path, cfg: DriveIndexConfig | None = None) -> dict:
    """Index a local folder directly into the SQLite search index."""
    c = cfg or default_config()
    return _index_local_directory(c.db_path, Path(path).expanduser().resolve(), ocr_pdf_enabled=c.ocr_enabled, ocr_image_enabled=c.ocr_image_enabled)


def selective_sync_plan_api(mapping_name: str | None = None, cfg: DriveIndexConfig | None = None) -> dict:
    """Generate selective sync plan for configured local-to-Drive mappings."""
    c = cfg or default_config()
    mappings = [m for m in c.sync_mappings if not mapping_name or m.name == mapping_name]
    if not mappings:
        return {"success": False, "error": f"No sync mapping found matching '{mapping_name}'"}
    
    from .core.crawler import build_drive_service, crawl
    service = build_drive_service(c.google_api_dir)
    drive_files = crawl(service, c.root_folder_id or "root", c.root_folder_name)
    
    results = []
    for m in mappings:
        loc_files = scan_local_directory(m.local_path, recursive=True, compute_hashes=True)
        plan = plan_selective_sync(m, loc_files, drive_files)
        results.append({
            "mapping": m.name,
            "to_upload": len(plan.to_upload),
            "to_download": len(plan.to_download),
            "conflicts": len(plan.conflicts),
            "in_sync": len(plan.in_sync),
        })
    return {"success": True, "plans": results}


__all__ = [
    "DriveFile",
    "LocalFile",
    "SyncMapping",
    "SyncPlan",
    "OrganizerPlan",
    "plan_incremental_actions",
    "build_index",
    "incremental_update",
    "reindex_metadata_only",
    "benchmark_ocr_parameters",
    "search",
    "status",
    "find_duplicates",
    "flag_old_files",
    "auto_organize_downloads",
    "organize_documents",
    "index_local_folder",
    "selective_sync_plan_api",
    "access_check",
    "analyse_first",
    "propose_plan",
    "validate_approval",
    "execute_on_approval",
    "format_plan_presentation",
    "intent_check",
    "safe_trash",
]
