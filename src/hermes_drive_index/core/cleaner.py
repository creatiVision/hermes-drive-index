"""File cleanup and organization algorithms implementing the 4 Claude cleanup skills.

Skill 1: Duplicate File Detector (exact duplicates, near-duplicates, version variants).
Skill 2: Old File Cleanup Assistant (tiered inventory: safe deletion, review needed, active/keep).
Skill 3: Auto-Organize Downloads (sort by type and date, flag duplicates).
Skill 4: Intelligent Folder Structuring (4-6 top-level categories, memorable naming, approval-first).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Iterable, Sequence

from .local_scanner import LocalFile, compute_file_hashes, scan_local_directory

# Extensions classified by standard categories
TYPE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Images": (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".tif",
        ".ico", ".raw", ".heic", ".psd", ".ai",
    ),
    "Documents": (
        ".pdf", ".docx", ".doc", ".txt", ".md", ".markdown", ".rtf", ".odt",
        ".pages", ".epub", ".tex",
    ),
    "Spreadsheets": (
        ".xlsx", ".xls", ".csv", ".tsv", ".ods", ".numbers",
    ),
    "Presentations": (
        ".pptx", ".ppt", ".key", ".odp",
    ),
    "Videos": (
        ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v",
    ),
    "Audio": (
        ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma",
    ),
    "Installers": (
        ".deb", ".rpm", ".dmg", ".pkg", ".iso", ".msi", ".exe", ".appimage",
    ),
    "Archives": (
        ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".zst",
    ),
    "Code": (
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml",
        ".yml", ".toml", ".sh", ".bash", ".zsh", ".c", ".cpp", ".h", ".rs",
        ".go", ".java", ".php", ".rb", ".sql",
    ),
}

# Inverted mapping: extension -> category
EXT_TO_CATEGORY: dict[str, str] = {}
for cat, exts in TYPE_CATEGORIES.items():
    for ext in exts:
        EXT_TO_CATEGORY[ext] = cat

# Obvious junk and temporary extensions safe to flag for deletion
SAFE_DELETE_EXTENSIONS = {
    ".tmp",
    ".temp",
    ".bak",
    ".backup",
    ".old",
    ".log",
    ".swp",
    ".swo",
    "~",
    ".ds_store",
    ".thumbs.db",
}

VERSION_PATTERNS = [
    re.compile(r"[-_ ]*(?:v\d+|\bv\d+\b|\bver\d+\b)", re.IGNORECASE),
    re.compile(r"[-_ ]*(?:final|real|draft)", re.IGNORECASE),
    re.compile(r"[-_ ]*(?:kopie|copy|\(\d+\))", re.IGNORECASE),
    re.compile(r"[-_ ]*(?:new|neu|latest|alt|old)", re.IGNORECASE),
]

_RE_UNDERSCORES = re.compile(r"[_\-]+")
_RE_SPACES = re.compile(r"\s+")


def normalize_stem(stem: str) -> str:
    """Normalize filename stem to find near-duplicates and version variants."""
    s = stem.lower()
    # Strip common copy and version annotations using pre-compiled regexes
    for pat in VERSION_PATTERNS:
        s = pat.sub("", s)
    s = _RE_UNDERSCORES.sub(" ", s)
    s = _RE_SPACES.sub(" ", s).strip()
    return s


# =====================================================================
# SKILL 1: DUPLICATE FILE DETECTOR
# =====================================================================

@dataclass
class DuplicateGroup:
    group_type: str  # "exact", "near", or "version_variant"
    match_key: str
    files: list[dict]
    recommended_keep_path: str
    reclaimable_bytes: int
    recommendation_reason: str


def detect_duplicates(
    files: Iterable[LocalFile | dict],
    *,
    check_exact: bool = True,
    check_near: bool = True,
    check_variants: bool = True,
) -> dict:
    """Scan files and categorize into exact duplicates, near-duplicates, and version variants.

    Returns full report with keep/delete recommendations and space reclamation estimate.
    """
    file_list: list[LocalFile] = []
    for f in files:
        if isinstance(f, LocalFile):
            file_list.append(f)
        elif isinstance(f, dict):
            p_str = f.get("path", "")
            f_name = f.get("name") or os.path.basename(p_str)
            f_ext = os.path.splitext(p_str)[1].lower()
            file_list.append(
                LocalFile(
                    id=f.get("id", p_str),
                    name=f_name,
                    mime_type=f.get("mime_type", ""),
                    path=p_str,
                    size=int(f.get("size", 0)),
                    modified_time=f.get("modified_time"),
                    accessed_time=f.get("accessed_time"),
                    md5_checksum=f.get("md5_checksum"),
                    sha256_checksum=f.get("sha256_checksum"),
                    extension=f_ext,
                )
            )

    # 1. Exact duplicates (grouped by size, then compute hash)
    exact_groups: list[DuplicateGroup] = []
    handled_paths: set[str] = set()

    if check_exact:
        by_size: dict[int, list[LocalFile]] = defaultdict(list)
        for f in file_list:
            if f.size > 0 and not f.is_dir:
                by_size[f.size].append(f)

        for size, candidates in by_size.items():
            if len(candidates) < 2:
                continue
            by_hash: dict[str, list[LocalFile]] = defaultdict(list)
            for c in candidates:
                # Compute checksum if not present
                md5 = c.md5_checksum
                if not md5 and Path(c.path).is_file():
                    try:
                        md5, _ = compute_file_hashes(c.path)
                        c.md5_checksum = md5
                    except OSError:
                        continue
                if md5:
                    by_hash[md5].append(c)

            for hash_val, dupes in by_hash.items():
                if len(dupes) > 1:
                    # Choose recommended keep: newest or shortest path
                    sorted_dupes = sorted(
                        dupes,
                        key=lambda x: (-(datetime.fromisoformat(x.modified_time).timestamp() if x.modified_time else 0), len(x.path)),
                    )
                    keep = sorted_dupes[0]
                    reclaimable = sum(d.size for d in sorted_dupes[1:])
                    for d in dupes:
                        handled_paths.add(d.path)
                    exact_groups.append(
                        DuplicateGroup(
                            group_type="exact",
                            match_key=f"MD5:{hash_val[:10]}",
                            files=[asdict(d) for d in sorted_dupes],
                            recommended_keep_path=keep.path,
                            reclaimable_bytes=reclaimable,
                            recommendation_reason="Byte-for-byte identical; recommend keeping newest file",
                        )
                    )

    # 2. Version variants and near-duplicates
    variant_groups: list[DuplicateGroup] = []
    near_groups: list[DuplicateGroup] = []

    if check_variants or check_near:
        by_stem: dict[tuple[str, str], list[tuple[LocalFile, str]]] = defaultdict(list)
        for f in file_list:
            if f.is_dir or f.path in handled_paths:
                continue
            stem = os.path.splitext(f.name)[0]
            norm = normalize_stem(stem)
            if len(norm) >= 3:
                by_stem[(norm, f.extension)].append((f, stem))

        for (norm_key, ext), cluster in by_stem.items():
            if len(cluster) < 2:
                continue

            has_version_marker = any(
                any(pat.search(stem) for pat in VERSION_PATTERNS)
                for _c, stem in cluster
            )

            # Pick keep candidate: prefer file with latest date
            sorted_cluster = sorted(
                [c for c, _stem in cluster],
                key=lambda x: (-(datetime.fromisoformat(x.modified_time).timestamp() if x.modified_time else 0), len(x.name)),
            )
            keep = sorted_cluster[0]
            reclaimable = sum(c.size for c in sorted_cluster[1:])

            if has_version_marker and check_variants:
                variant_groups.append(
                    DuplicateGroup(
                        group_type="version_variant",
                        match_key=f"{norm_key}{ext}",
                        files=[asdict(c) for c in sorted_cluster],
                        recommended_keep_path=keep.path,
                        reclaimable_bytes=reclaimable,
                        recommendation_reason="Detected version suffix variants (e.g. _v2, _final, copy); verify which one is final",
                    )
                )
            elif check_near:
                near_groups.append(
                    DuplicateGroup(
                        group_type="near",
                        match_key=f"{norm_key}{ext}",
                        files=[asdict(c) for c in sorted_cluster],
                        recommended_keep_path=keep.path,
                        reclaimable_bytes=reclaimable,
                        recommendation_reason="Near identical names with minor formatting differences",
                    )
                )

    all_groups = exact_groups + variant_groups + near_groups
    total_reclaimable = sum(g.reclaimable_bytes for g in all_groups)

    return {
        "total_groups": len(all_groups),
        "exact_duplicates_count": len(exact_groups),
        "version_variants_count": len(variant_groups),
        "near_duplicates_count": len(near_groups),
        "total_reclaimable_bytes": total_reclaimable,
        "total_reclaimable_mb": round(total_reclaimable / (1024 * 1024), 2),
        "groups": [asdict(g) for g in all_groups],
    }


# =====================================================================
# SKILL 2: OLD FILE CLEANUP ASSISTANT
# =====================================================================

@dataclass
class OldFileItem:
    path: str
    name: str
    size_bytes: int
    modified_time: str | None
    age_days: int
    category: str
    reason: str


def classify_old_files(
    files: Iterable[LocalFile | dict],
    *,
    days_threshold: int = 90,
    installer_threshold_days: int = 30,
) -> dict:
    """Analyze files by age, type, and usage patterns into a tiered inventory:

    - Tier 1: Safe deletion candidates (temp files, old installers, logs, cache).
    - Tier 2: Review needed (untouched files > threshold days).
    - Tier 3: Active / Keep (recent files).
    """
    now = datetime.now(timezone.utc)
    tier1_safe: list[OldFileItem] = []
    tier2_review: list[OldFileItem] = []
    tier3_active: list[OldFileItem] = []

    for f in files:
        if isinstance(f, LocalFile):
            path_str = f.path
            name = f.name
            size = f.size
            mtime_str = f.modified_time
            ext = f.extension or os.path.splitext(path_str)[1].lower()
        else:
            path_str = f.get("path", "")
            name = f.get("name") or os.path.basename(path_str)
            size = int(f.get("size", 0))
            mtime_str = f.get("modified_time")
            ext = os.path.splitext(path_str)[1].lower()

        age_days = 0
        if mtime_str:
            try:
                mtime = datetime.fromisoformat(mtime_str)
                age_days = max(0, int((now - mtime).total_seconds() / 86400))
            except Exception:
                age_days = 0

        # Tier 1 checks:
        if ext in SAFE_DELETE_EXTENSIONS or name.endswith("~") or name.startswith(".#"):
            tier1_safe.append(
                OldFileItem(
                    path=path_str,
                    name=name,
                    size_bytes=size,
                    modified_time=mtime_str,
                    age_days=age_days,
                    category="temp_or_junk",
                    reason=f"Temporary/junk file extension ({ext or name})",
                )
            )
        elif ext in TYPE_CATEGORIES["Installers"] and age_days >= installer_threshold_days:
            tier1_safe.append(
                OldFileItem(
                    path=path_str,
                    name=name,
                    size_bytes=size,
                    modified_time=mtime_str,
                    age_days=age_days,
                    category="old_installer",
                    reason=f"Software installer older than {installer_threshold_days} days ({age_days} days old)",
                )
            )
        elif ext in TYPE_CATEGORIES["Archives"] and age_days >= days_threshold and ("Downloads" in path_str or "tmp" in path_str):
            tier1_safe.append(
                OldFileItem(
                    path=path_str,
                    name=name,
                    size_bytes=size,
                    modified_time=mtime_str,
                    age_days=age_days,
                    category="old_download_archive",
                    reason=f"Downloaded archive untouched for {age_days} days",
                )
            )
        # Tier 2: Review needed
        elif age_days >= days_threshold:
            tier2_review.append(
                OldFileItem(
                    path=path_str,
                    name=name,
                    size_bytes=size,
                    modified_time=mtime_str,
                    age_days=age_days,
                    category=EXT_TO_CATEGORY.get(ext, "Other"),
                    reason=f"Untouched for {age_days} days (> {days_threshold} days threshold)",
                )
            )
        # Tier 3: Active / Keep
        else:
            tier3_active.append(
                OldFileItem(
                    path=path_str,
                    name=name,
                    size_bytes=size,
                    modified_time=mtime_str,
                    age_days=age_days,
                    category=EXT_TO_CATEGORY.get(ext, "Other"),
                    reason="Active or recently modified",
                )
            )

    tier1_bytes = sum(item.size_bytes for item in tier1_safe)
    tier2_bytes = sum(item.size_bytes for item in tier2_review)

    return {
        "threshold_days": days_threshold,
        "safe_deletion_candidates": {
            "count": len(tier1_safe),
            "total_bytes": tier1_bytes,
            "total_mb": round(tier1_bytes / (1024 * 1024), 2),
            "items": [asdict(i) for i in tier1_safe],
        },
        "review_needed": {
            "count": len(tier2_review),
            "total_bytes": tier2_bytes,
            "total_mb": round(tier2_bytes / (1024 * 1024), 2),
            "items": [asdict(i) for i in tier2_review],
        },
        "active_files_count": len(tier3_active),
    }


# =====================================================================
# SKILL 3: AUTO-ORGANIZE DOWNLOADS
# =====================================================================

def plan_download_organization(
    folder_path: Path | str,
    *,
    by_date: bool = True,
    detect_dupes: bool = True,
) -> dict:
    """Sort a flat Downloads folder into subfolders by type and optionally date."""
    base = Path(folder_path).resolve()
    files = scan_local_directory(base, recursive=False, compute_hashes=detect_dupes)

    moves: list[dict] = []
    folders_to_create: set[str] = set()
    category_counts: dict[str, int] = defaultdict(int)

    for f in files:
        if f.is_dir:
            continue
        ext = f.extension or os.path.splitext(f.name)[1].lower()
        cat = EXT_TO_CATEGORY.get(ext, "Other")
        category_counts[cat] += 1

        if by_date and f.modified_time and len(f.modified_time) >= 4:
            year = f.modified_time[:4]
            dest_dir = base / cat / year
        else:
            dest_dir = base / cat

        folders_to_create.add(str(dest_dir))
        dest_path = dest_dir / f.name

        moves.append({
            "source_path": f.path,
            "target_path": str(dest_path),
            "category": cat,
            "file_name": f.name,
            "size_bytes": f.size,
        })

    duplicates_report = detect_duplicates(files) if detect_dupes else None

    return {
        "folder": str(base),
        "total_files": len(files),
        "categories_found": dict(category_counts),
        "folders_to_create": sorted(list(folders_to_create)),
        "planned_moves": moves,
        "duplicates_detected": duplicates_report,
    }


# =====================================================================
# SKILL 4: INTELLIGENT FOLDER STRUCTURING (DOCUMENTS)
# =====================================================================

TOP_LEVEL_STRUCTURE = [
    ("01-Projects", re.compile(r"project|code|repo|git|build|dev|design|app", re.IGNORECASE)),
    ("02-Finances", re.compile(r"invoice|receipt|rechnung|beleg|steuer|tax|bank|konto|finanz|payment|vertrag|contract", re.IGNORECASE)),
    ("03-Personal", re.compile(r"personal|privat|id|ausweis|pass|krankenkasse|health|insurance|versicherung|urlaub|travel", re.IGNORECASE)),
    ("04-Reference", re.compile(r"guide|handbook|reference|manual|doc|template|vorlage|book|cheat|tutorial", re.IGNORECASE)),
    ("05-Archive", re.compile(r"archive|archiv|old|alt|backup|bak|201\d|202[0-3]", re.IGNORECASE)),
    ("06-Inbox-Unsorted", re.compile(r".*", re.IGNORECASE)),
]


def plan_document_structure(
    folder_path: Path | str,
    *,
    user_search_mode: str = "by_category",
    detect_dupes: bool = True,
) -> dict:
    """Analyze a documents folder and propose a clean 4-6 top-level folder hierarchy."""
    base = Path(folder_path).resolve()
    files = scan_local_directory(base, recursive=True, compute_hashes=detect_dupes)

    folders_to_create: set[str] = set()
    planned_moves: list[dict] = []
    unclassified: list[dict] = []

    for top, _ in TOP_LEVEL_STRUCTURE:
        folders_to_create.add(str(base / top))

    for f in files:
        if f.is_dir:
            continue
        rel_parts = Path(f.path).relative_to(base).parts
        # If already placed in one of the top categories, don't re-move
        if len(rel_parts) > 1 and rel_parts[0] in [t[0] for t in TOP_LEVEL_STRUCTURE]:
            continue

        assigned = None
        for folder_name, pat in TOP_LEVEL_STRUCTURE[:-1]:
            if pat.search(f.name) or pat.search(f.path):
                assigned = folder_name
                break

        if assigned:
            dest_dir = base / assigned
            dest_path = dest_dir / f.name
            planned_moves.append({
                "source_path": f.path,
                "target_path": str(dest_path),
                "folder": assigned,
                "file_name": f.name,
                "size_bytes": f.size,
            })
        else:
            unclassified.append({
                "path": f.path,
                "name": f.name,
                "size_bytes": f.size,
                "reason": "Does not match standard project/finance/personal/reference patterns",
            })

    duplicates_report = detect_duplicates(files) if detect_dupes else None

    return {
        "folder": str(base),
        "total_files": len(files),
        "folders_to_create": sorted(list(folders_to_create)),
        "planned_moves": planned_moves,
        "unclassified_files": unclassified,
        "duplicates_detected": duplicates_report,
    }
