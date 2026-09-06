"""Selective sync between designated local folders and Google Drive.

Allows users to configure specific local folders to synchronize with specific
Google Drive paths, while leaving all other local and remote folders untouched.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import fnmatch
from pathlib import Path
from typing import Any, Iterable, Sequence

from .crawler import cache_path, download_or_export
from .local_scanner import LocalFile, compute_file_hashes, scan_local_directory
from .models import DriveFile
from .organize import ensure_folder_path


@dataclass
class SyncMapping:
    """Configured selective sync mapping between a local directory and a Drive path."""

    name: str
    local_path: Path
    drive_folder_path: str
    drive_folder_id: str | None = None
    direction: str = "bidirectional"  # "bidirectional", "push", "pull"
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()


@dataclass
class SyncItem:
    relative_path: str
    action: str  # "upload", "download", "conflict", "in_sync"
    local_file: dict | None = None
    drive_file: dict | None = None
    reason: str = ""


@dataclass
class SyncPlan:
    mapping_name: str
    local_root: str
    drive_root: str
    direction: str
    items: list[SyncItem] = field(default_factory=list)
    to_upload: list[SyncItem] = field(default_factory=list)
    to_download: list[SyncItem] = field(default_factory=list)
    conflicts: list[SyncItem] = field(default_factory=list)
    in_sync: list[SyncItem] = field(default_factory=list)


def file_matches_filters(
    rel_path: str,
    include_patterns: Sequence[str] = (),
    exclude_patterns: Sequence[str] = (),
) -> bool:
    """Check if relative path matches include/exclude glob filters."""
    if exclude_patterns:
        for pat in exclude_patterns:
            if fnmatch.fnmatch(rel_path, pat):
                return False
    if include_patterns:
        return any(fnmatch.fnmatch(rel_path, pat) for pat in include_patterns)
    return True


def plan_selective_sync(
    mapping: SyncMapping,
    local_files: Sequence[LocalFile],
    drive_files: Sequence[DriveFile],
) -> SyncPlan:
    """Compare local directory and Drive folder to produce a sync plan."""
    plan = SyncPlan(
        mapping_name=mapping.name,
        local_root=str(mapping.local_path),
        drive_root=mapping.drive_folder_path,
        direction=mapping.direction,
    )

    # Index local files by relative path
    local_by_rel: dict[str, LocalFile] = {}
    for lf in local_files:
        if lf.is_dir:
            continue
        rel = lf.relative_path or str(Path(lf.path).relative_to(mapping.local_path))
        if file_matches_filters(rel, mapping.include_patterns, mapping.exclude_patterns):
            local_by_rel[rel] = lf

    # Index drive files by path relative to mapping.drive_folder_path
    drive_by_rel: dict[str, DriveFile] = {}
    prefix = mapping.drive_folder_path.strip("/")
    for df in drive_files:
        df_path = df.path.strip("/")
        if df_path == prefix:
            continue
        if df_path.startswith(prefix + "/"):
            rel = df_path[len(prefix) + 1:]
            if file_matches_filters(rel, mapping.include_patterns, mapping.exclude_patterns):
                drive_by_rel[rel] = df

    all_rel_paths = sorted(set(local_by_rel.keys()) | set(drive_by_rel.keys()))

    for rel in all_rel_paths:
        loc = local_by_rel.get(rel)
        drv = drive_by_rel.get(rel)

        # File exists only locally
        if loc and not drv:
            if mapping.direction in {"bidirectional", "push"}:
                item = SyncItem(
                    relative_path=rel,
                    action="upload",
                    local_file=asdict(loc),
                    reason="File exists only locally; upload to Drive",
                )
                plan.to_upload.append(item)
            else:
                item = SyncItem(
                    relative_path=rel,
                    action="skip",
                    local_file=asdict(loc),
                    reason="Pull-only sync mode: local-only file not uploaded",
                )
            plan.items.append(item)

        # File exists only on Drive
        elif drv and not loc:
            if mapping.direction in {"bidirectional", "pull"}:
                item = SyncItem(
                    relative_path=rel,
                    action="download",
                    drive_file={"id": drv.id, "name": drv.name, "path": drv.path, "size": drv.size, "mime_type": drv.mime_type},
                    reason="File exists only on Drive; download to local",
                )
                plan.to_download.append(item)
            else:
                item = SyncItem(
                    relative_path=rel,
                    action="skip",
                    drive_file={"id": drv.id, "name": drv.name, "path": drv.path},
                    reason="Push-only sync mode: remote-only file not downloaded",
                )
            plan.items.append(item)

        # File exists both locally and on Drive
        elif loc and drv:
            # Check checksum if available
            checksum_match = bool(loc.md5_checksum and drv.md5_checksum and loc.md5_checksum.lower() == drv.md5_checksum.lower())
            size_match = loc.size == drv.size

            if checksum_match or (loc.md5_checksum is None and size_match):
                item = SyncItem(
                    relative_path=rel,
                    action="in_sync",
                    local_file=asdict(loc),
                    drive_file={"id": drv.id, "name": drv.name, "path": drv.path},
                    reason="Files match in size/checksum",
                )
                plan.in_sync.append(item)
            else:
                # Timestamps comparison
                loc_mtime = datetime.fromisoformat(loc.modified_time) if loc.modified_time else None
                drv_mtime = datetime.fromisoformat(drv.modified_time.replace("Z", "+00:00")) if drv.modified_time else None

                if loc_mtime and drv_mtime:
                    if loc_mtime > drv_mtime:
                        action = "upload" if mapping.direction in {"bidirectional", "push"} else "conflict"
                        reason = "Local file is newer than Drive copy"
                    elif drv_mtime > loc_mtime:
                        action = "download" if mapping.direction in {"bidirectional", "pull"} else "conflict"
                        reason = "Drive file is newer than local copy"
                    else:
                        action = "conflict"
                        reason = "Different sizes/checksums with same timestamp"
                else:
                    action = "conflict"
                    reason = "Different sizes/checksums and unresolvable timestamps"

                item = SyncItem(
                    relative_path=rel,
                    action=action,
                    local_file=asdict(loc),
                    drive_file={"id": drv.id, "name": drv.name, "path": drv.path},
                    reason=reason,
                )
                if action == "upload":
                    plan.to_upload.append(item)
                elif action == "download":
                    plan.to_download.append(item)
                else:
                    plan.conflicts.append(item)
            plan.items.append(item)

    return plan


def apply_selective_sync(
    service: Any,
    root_id: str,
    root_name: str,
    mapping: SyncMapping,
    plan: SyncPlan,
    *,
    dry_run: bool = True,
) -> dict:
    """Execute planned uploads/downloads between local and Drive folders."""
    if dry_run:
        return {
            "dry_run": True,
            "mapping": mapping.name,
            "uploads_planned": len(plan.to_upload),
            "downloads_planned": len(plan.to_download),
            "conflicts": len(plan.conflicts),
            "in_sync": len(plan.in_sync),
            "summary": f"Dry-run: {len(plan.to_upload)} files to upload, {len(plan.to_download)} to download, {len(plan.conflicts)} conflicts.",
        }

    from googleapiclient.http import MediaFileUpload  # type: ignore

    uploaded_count = 0
    downloaded_count = 0
    errors: list[dict] = []

    # Process uploads
    for item in plan.to_upload:
        try:
            rel = Path(item.relative_path)
            local_file_path = mapping.local_path / rel
            target_drive_folder = str(Path(mapping.drive_folder_path) / rel.parent)
            parent_id = ensure_folder_path(service, root_id, root_name, target_drive_folder)

            media = MediaFileUpload(str(local_file_path), resumable=True)
            body = {"name": rel.name, "parents": [parent_id]}
            service.files().create(body=body, media_body=media, supportsAllDrives=True).execute()
            uploaded_count += 1
        except Exception as exc:
            errors.append({"action": "upload", "path": item.relative_path, "error": str(exc)})

    # Process downloads
    for item in plan.to_download:
        try:
            rel = Path(item.relative_path)
            local_target = mapping.local_path / rel
            local_target.parent.mkdir(parents=True, exist_ok=True)
            df_info = item.drive_file or {}
            df = DriveFile(
                id=df_info["id"],
                name=df_info["name"],
                mime_type=df_info.get("mime_type", ""),
                path=df_info.get("path", ""),
                size=df_info.get("size", 0),
                modified_time=None,
                md5_checksum=None,
                web_view_link=None,
            )
            tmp_cache = mapping.local_path / ".sync_tmp"
            tmp_cache.mkdir(parents=True, exist_ok=True)
            downloaded = download_or_export(service, tmp_cache, df)
            if downloaded and downloaded.exists():
                downloaded.replace(local_target)
                downloaded_count += 1
        except Exception as exc:
            errors.append({"action": "download", "path": item.relative_path, "error": str(exc)})

    return {
        "dry_run": False,
        "mapping": mapping.name,
        "uploaded": uploaded_count,
        "downloaded": downloaded_count,
        "conflicts": len(plan.conflicts),
        "errors": errors,
        "success": len(errors) == 0,
    }
