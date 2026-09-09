#!/usr/bin/env python3
"""
Host Filesystem Tree Collector for Hermes Drive Index & Multi-Computer Dashboard.

Scans all real physical mount points and partitions on the host system:
- / (Root ext4)
- /home (/home/mb)
- /media/work-data
- /media/privat-data
- /media/xchg
- /media/nosync
- /media/empty
(and any other mounted block devices).

Gathers technical details:
- Real hierarchy & subfolders up to configurable depth
- Mount devices, filesystem types, partition total/used/free space
- Directory permissions (POSIX octal & mode string), owner & group
- Direct and recursive file counts & sizes
- Syncthing sync mapping (Folder ID, label, sync type, connected peer devices)
- Backup coverage (pg-backup.sh, docker-backup.sh, hermes-backup-config.sh, Timeshift, rclone, etc.)

Outputs to /media/xchg/ai-tools-data/system_filesystem_tree.json for direct access
by host tools, LAN peers via Syncthing, and the containerized Hermes dashboard.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("filesystem-collector")

DEFAULT_OUTPUT_PATH = Path("/media/xchg/ai-tools-data/system_filesystem_tree.json")
FALLBACK_OUTPUT_PATH = Path.home() / ".hermes" / "system_filesystem_tree.json"

# Pseudo / virtual filesystem types and paths to strictly avoid
PSEUDO_FSTYPES = {
    "proc", "sysfs", "devtmpfs", "tmpfs", "securityfs", "cgroup", "cgroup2",
    "pstore", "bpf", "autofs", "hugetlbfs", "mqueue", "debugfs", "tracefs",
    "fusectl", "configfs", "ramfs", "devpts", "efivarfs", "binfmt_misc", "overlay"
}

IGNORE_DIR_NAMES = {
    ".git", ".snapshots", "proc", "sys", "dev", "run", "tmp", "var/tmp",
    "lost+found", ".Trash", ".trash", "node_modules", "__pycache__", ".venv",
    ".cache", ".npm", ".cargo", ".rustup"
}

# Known backup programs mapped to path regex / prefixes
BACKUP_REGISTRY: List[Dict[str, Any]] = [
    {
        "pattern": r"^/media/empty/timeshift",
        "program": "Timeshift",
        "schedule": "Täglich Snapshot",
        "target": "/media/empty/timeshift",
        "retention": "Systemwiederherstellungspunkte",
    },
    {
        "pattern": r"^/media/empty/bckp_thunderbird",
        "program": "Thunderbird Backup",
        "schedule": "Periodisch",
        "target": "/media/empty/bckp_thunderbird",
        "retention": "Mailprofil-Sicherung",
    },
    {
        "pattern": r"^/media/xchg/ai-tools-data/postgres-backups",
        "program": "pg-backup.sh",
        "schedule": "03:00 Täglich & Boot",
        "target": "/media/xchg/ai-tools-data/postgres-backups",
        "retention": "7 Tage daily / 12 Monate monthly",
    },
    {
        "pattern": r"^/media/xchg/ai-tools-data/docker-backups",
        "program": "docker-backup.sh",
        "schedule": "03:00 Täglich",
        "target": "/media/xchg/ai-tools-data/docker-backups",
        "retention": "Docker Volume Tarballs",
    },
    {
        "pattern": r"^/media/xchg/ai-agents-workspaces/hermes",
        "program": "hermes-backup-config.sh",
        "schedule": "Stündlich (0 * * * *)",
        "target": "/media/xchg/ai-agents-workspaces/hermes/backups",
        "retention": "24h Snapshots",
    },
    {
        "pattern": r"^/media/work-data/001_cv-bookaccount",
        "program": "rclone gdrive sync",
        "schedule": "Periodisch & PG Dump",
        "target": "gdrive://creatiVision/Accounting",
        "retention": "Cloud Versioning (Audit-Proof)",
    },
    {
        "pattern": r"^/media/privat-data/10_PrivatBüro",
        "program": "pg-backup + rclone gdrive",
        "schedule": "Monatlich + Cloud",
        "target": "gdrive://creatiVision/PrivatBüro",
        "retention": "Permanent",
    },
]


def _get_mode_str(mode: int) -> str:
    """Converts a stat mode to a standard ls-like string (e.g. drwxr-xr-x)."""
    is_dir = "d" if stat.S_ISDIR(mode) else "-"
    perms = [
        "r" if mode & stat.S_IRUSR else "-",
        "w" if mode & stat.S_IWUSR else "-",
        "x" if mode & stat.S_IXUSR else "-",
        "r" if mode & stat.S_IRGRP else "-",
        "w" if mode & stat.S_IWGRP else "-",
        "x" if mode & stat.S_IXGRP else "-",
        "r" if mode & stat.S_IROTH else "-",
        "w" if mode & stat.S_IWOTH else "-",
        "x" if mode & stat.S_IXOTH else "-",
    ]
    return is_dir + "".join(perms)


def _load_syncthing_folders() -> List[Dict[str, Any]]:
    """Parses Syncthing folders from ~/.config/syncthing/config.xml."""
    candidates = [
        Path.home() / ".config" / "syncthing" / "config.xml",
        Path("/home/mb/.config/syncthing/config.xml"),
    ]
    cfg_file = None
    for c in candidates:
        if c.is_file():
            cfg_file = c
            break

    if not cfg_file:
        return []

    try:
        tree = ET.parse(cfg_file)
        root = tree.getroot()

        # Parse devices mapping id -> name
        devices: Dict[str, str] = {}
        for dev in root.findall(".//device"):
            did = dev.attrib.get("id", "")
            dname = dev.attrib.get("name", did[:7])
            if did:
                devices[did] = dname

        folders = []
        for f in root.findall(".//folder"):
            fpath = f.attrib.get("path", "")
            fid = f.attrib.get("id", "")
            flabel = f.attrib.get("label", fid)
            ftype = f.attrib.get("type", "sendreceive")
            if not fpath:
                continue
            if fpath.startswith("~"):
                fpath = os.path.expanduser(fpath)
            fpath = os.path.abspath(fpath)

            peer_names = []
            for d in f.findall("device"):
                pd_id = d.attrib.get("id", "")
                if pd_id in devices:
                    peer_names.append(devices[pd_id])

            folders.append({
                "folder_id": fid,
                "label": flabel,
                "path": fpath,
                "type": ftype,
                "peers": peer_names,
            })
        return folders
    except Exception as exc:
        logger.warning("Failed to parse Syncthing config: %s", exc)
        return []


def _match_syncthing(path: str, st_folders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Matches a directory path to the best corresponding Syncthing folder."""
    best = None
    best_len = 0
    for f in st_folders:
        fpath = f["path"]
        if path == fpath or path.startswith(fpath + "/"):
            if len(fpath) > best_len:
                best = f
                best_len = len(fpath)

    if best:
        return {
            "synced": True,
            "folder_id": best["folder_id"],
            "label": best["label"],
            "type": best["type"],
            "peers": best["peers"],
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


def _match_backup(path: str) -> Dict[str, Any]:
    """Checks if a directory path matches known backup routines."""
    for reg in BACKUP_REGISTRY:
        if re.search(reg["pattern"], path):
            return {
                "protected": True,
                "program": reg["program"],
                "schedule": reg["schedule"],
                "target": reg["target"],
                "retention": reg["retention"],
            }
    return {
        "protected": False,
        "program": None,
        "schedule": None,
        "target": None,
        "retention": None,
    }


def _discover_mount_points() -> List[Dict[str, Any]]:
    """Discovers all real physical mount points from /proc/mounts and standard mounts."""
    mounts: List[Dict[str, Any]] = []
    seen_points: Set[str] = set()

    priority_order = [
        "/media/work-data",
        "/media/privat-data",
        "/media/xchg",
        "/media/nosync",
        "/media/empty",
        "/home",
        "/",
    ]

    try:
        with open("/proc/mounts", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                dev, mpoint, fstype = parts[0], parts[1], parts[2]

                if fstype in PSEUDO_FSTYPES:
                    continue
                if not dev.startswith("/dev/") and not fstype.startswith("fuse"):
                    continue
                if mpoint in seen_points:
                    continue
                if any(mpoint.startswith(prefix) for prefix in ["/var/lib/docker", "/snap", "/var/snap", "/run", "/boot"]):
                    continue

                seen_points.add(mpoint)
                mounts.append({
                    "device": dev,
                    "mount_point": mpoint,
                    "fstype": fstype,
                })
    except Exception as exc:
        logger.warning("Could not read /proc/mounts: %s", exc)

    standard_targets = [
        ("/media/work-data", "Arbeitsdateien & Kundenprojekte"),
        ("/media/privat-data", "Privatarchiv & Steuerunterlagen"),
        ("/media/xchg", "Geteilter Datenaustausch & AI Runtimes"),
        ("/media/nosync", "Lokaler Großspeicher (Media & Caches)"),
        ("/media/empty", "Sicherungs-Partition (Timeshift & Mails)"),
        ("/home", "Home Verzeichnisse"),
        ("/", "Root Systemdateien (OS)"),
    ]

    for m_path, m_label in standard_targets:
        if os.path.exists(m_path) and m_path not in seen_points:
            mounts.append({
                "device": "auto",
                "mount_point": m_path,
                "fstype": "ext4",
                "custom_label": m_label,
            })
            seen_points.add(m_path)

    def sort_key(m: Dict[str, Any]) -> int:
        pt = m["mount_point"]
        if pt in priority_order:
            return priority_order.index(pt)
        if pt.startswith("/media"):
            return 10
        return 50

    mounts.sort(key=sort_key)
    return mounts


def _scan_directory_node(
    path: str,
    depth: int,
    max_depth: int,
    mount_info: Dict[str, Any],
    st_folders: List[Dict[str, Any]],
    current_depth: int = 0
) -> Dict[str, Any]:
    """Recursively scans a directory node and constructs detailed metadata."""
    basename = os.path.basename(path) or path
    node_id = "node_" + re.sub(r"[^a-zA-Z0-9_-]", "_", path.strip("/"))

    direct_files = 0
    direct_dirs = 0
    direct_bytes = 0
    children_nodes = []
    readable = True

    try:
        st = os.stat(path)
        mode = st.st_mode
        mode_str = _get_mode_str(mode)
        mode_octal = oct(stat.S_IMODE(mode))
        uid = st.st_uid
        gid = st.st_gid
        mtime_iso = dt.datetime.fromtimestamp(st.st_mtime, tz=dt.timezone.utc).isoformat()
    except Exception:
        mode_str = "drwxr-xr-x"
        mode_octal = "0755"
        uid, gid = 1000, 1000
        mtime_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        readable = False

    try:
        import pwd
        owner_name = pwd.getpwuid(uid).pw_name
    except Exception:
        owner_name = str(uid)
    try:
        import grp
        group_name = grp.getgrgid(gid).gr_name
    except Exception:
        group_name = str(gid)

    if readable:
        try:
            entries = []
            with os.scandir(path) as it:
                for entry in it:
                    if entry.name.startswith(".") and entry.name != ".stglobalignore":
                        continue
                    if entry.name in IGNORE_DIR_NAMES:
                        continue
                    entries.append(entry)

            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        direct_dirs += 1
                        if current_depth < max_depth:
                            child_node = _scan_directory_node(
                                entry.path,
                                depth,
                                max_depth,
                                mount_info,
                                st_folders,
                                current_depth=current_depth + 1
                            )
                            children_nodes.append(child_node)
                    elif entry.is_file(follow_symlinks=False):
                        direct_files += 1
                        try:
                            direct_bytes += entry.stat().st_size
                        except Exception:
                            pass
                except Exception:
                    continue

        except PermissionError:
            readable = False
        except Exception as exc:
            logger.debug("Error reading %s: %s", path, exc)
            readable = False

    children_nodes.sort(key=lambda c: c["name"].lower())

    approx_files = direct_files + sum(c.get("approx_total_files", 0) for c in children_nodes)
    approx_bytes = direct_bytes + sum(c.get("approx_total_bytes", 0) for c in children_nodes)

    sync_info = _match_syncthing(path, st_folders)
    backup_info = _match_backup(path)

    if path == mount_info.get("mount_point"):
        node_type = "mount"
    elif children_nodes or direct_dirs > 0:
        node_type = "folder"
    else:
        node_type = "subfolder"

    if sync_info["synced"] and backup_info["protected"]:
        status_state = "PROTECTED_SYNCED"
        status_color = "#10b981"
        status_symbol = "🟢"
        status_label = "Synchronisiert & Gesichert"
    elif sync_info["synced"]:
        status_state = "SYNCED"
        status_color = "#06b6d4"
        status_symbol = "🔄"
        status_label = "Syncthing Mesh"
    elif backup_info["protected"]:
        status_state = "PROTECTED"
        status_color = "#a855f7"
        status_symbol = "🟣"
        status_label = "Backup Gesichert"
    elif not readable:
        status_state = "LOCKED"
        status_color = "#ef4444"
        status_symbol = "🔒"
        status_label = "Zugriff beschränkt"
    else:
        status_state = "LOCAL_ONLY"
        status_color = "#64748b"
        status_symbol = "⚪"
        status_label = "Lokales Dateisystem"

    return {
        "id": node_id,
        "name": basename,
        "path": path,
        "node_type": node_type,
        "mount_point": mount_info.get("mount_point"),
        "device": mount_info.get("device"),
        "fstype": mount_info.get("fstype"),
        "permissions": {
            "mode_str": mode_str,
            "mode_octal": mode_octal,
            "owner": owner_name,
            "group": group_name,
            "readable": readable,
        },
        "mtime": mtime_iso,
        "direct_files_count": direct_files,
        "direct_subdirs_count": direct_dirs,
        "approx_total_files": approx_files,
        "approx_total_bytes": approx_bytes,
        "approx_size_mb": round(approx_bytes / (1024 * 1024), 2),
        "status": {
            "state": status_state,
            "color": status_color,
            "symbol": status_symbol,
            "label": status_label,
        },
        "syncthing": sync_info,
        "backup": backup_info,
        "children": children_nodes,
    }


def collect_filesystem_tree(max_depth: int = 2) -> Dict[str, Any]:
    """Scans all mounts and constructs the full system filesystem tree."""
    hostname = socket.gethostname()
    scanned_at = dt.datetime.now(dt.timezone.utc).isoformat()
    mount_points = _discover_mount_points()
    st_folders = _load_syncthing_folders()

    logger.info("Starting scan on host %s across %d mount points (max_depth=%d)", hostname, len(mount_points), max_depth)

    mount_nodes = []
    total_space_bytes = 0
    total_used_bytes = 0
    total_free_bytes = 0

    for m in mount_points:
        mp = m["mount_point"]
        if not os.path.exists(mp):
            continue

        try:
            usage = shutil.disk_usage(mp)
            total_b = usage.total
            used_b = usage.used
            free_b = usage.free
            pct = round((used_b / total_b) * 100, 1) if total_b > 0 else 0.0
            if m["device"] != "auto" and not m["device"].startswith("/dev/loop"):
                total_space_bytes += total_b
                total_used_bytes += used_b
                total_free_bytes += free_b
        except Exception:
            total_b, used_b, free_b, pct = 0, 0, 0, 0.0

        node = _scan_directory_node(
            path=mp,
            depth=0,
            max_depth=max_depth,
            mount_info=m,
            st_folders=st_folders,
            current_depth=0
        )

        node["disk"] = {
            "total_bytes": total_b,
            "used_bytes": used_b,
            "free_bytes": free_b,
            "total_gb": round(total_b / (1024**3), 1),
            "used_gb": round(used_b / (1024**3), 1),
            "free_gb": round(free_b / (1024**3), 1),
            "percent_used": pct,
        }
        mount_nodes.append(node)

    result = {
        "schema_version": "2.0.0",
        "scanner": "collect_system_filesystem_tree.py",
        "scanned_at": scanned_at,
        "host": {
            "hostname": hostname,
            "user": os.getenv("USER", "mb"),
            "platform": sys.platform,
            "total_storage_gb": round(total_space_bytes / (1024**3), 1),
            "used_storage_gb": round(total_used_bytes / (1024**3), 1),
            "free_storage_gb": round(total_free_bytes / (1024**3), 1),
        },
        "mount_points_count": len(mount_nodes),
        "syncthing_folders_detected": len(st_folders),
        "mounts": mount_nodes,
    }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect complete system filesystem tree and synchronization status.")
    parser.add_argument("--depth", type=int, default=2, help="Directory scan recursion depth (default: 2)")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_PATH), help="Output JSON path")
    parser.add_argument("--quiet", action="store_true", help="Suppress logging")
    args = parser.parse_args()

    if args.quiet:
        logger.setLevel(logging.WARNING)

    tree = collect_filesystem_tree(max_depth=args.depth)
    out_path = Path(args.output)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
        logger.info("Successfully exported system filesystem tree to %s (%d mounts)", out_path, len(tree["mounts"]))
    except Exception as exc:
        logger.error("Failed writing to primary output %s: %s. Trying fallback %s", out_path, exc, FALLBACK_OUTPUT_PATH)
        FALLBACK_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FALLBACK_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
        logger.info("Wrote system tree to fallback %s", FALLBACK_OUTPUT_PATH)


if __name__ == "__main__":
    main()
