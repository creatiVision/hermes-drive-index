"""
Docker Mount Discovery and Path Translation Service.

Hermes runs inside a Docker container with host-to-container mount mappings
(e.g., Host /home/mb/Downloads -> Container /opt/data/downloads).
This module discovers active mounts, provides bidirectional path translation,
and validates that destination directories are within writable container boundaries.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import http.client
import json
import logging
import os
from pathlib import Path
import shutil
import socket
from typing import Any, Dict, List, Optional
import urllib.request

logger = logging.getLogger("hermes.storage.docker_mounts")

# Default mapping for Hermes container setup if socket / inspect is unavailable
KNOWN_HERMES_MOUNTS: List[Dict[str, Any]] = [
    {
        "host_path": "/home/mb/Downloads",
        "container_path": "/opt/data/downloads",
        "rw": True,
        "label": "Downloads (Dumpzone)",
        "category": "Dumpzone",
        "description": "Lokaler Download-Ordner für neu eingegangene Dateien",
    },
    {
        "host_path": "/home/mb/Schreibtisch",
        "container_path": "/opt/data/desktop",
        "rw": True,
        "label": "Schreibtisch (Desktop)",
        "category": "Dumpzone",
        "description": "Desktop-Ablage für temporäre Dateien",
    },
    {
        "host_path": "/home/mb/Dokumente",
        "container_path": "/opt/data/dokumente",
        "rw": True,
        "label": "Dokumente",
        "category": "Host Work",
        "description": "Persönlicher Dokumente-Ordner des Host-Benutzers",
    },
    {
        "host_path": "/home/mb/Bilder",
        "container_path": "/opt/data/bilder",
        "rw": True,
        "label": "Bilder / Fotos",
        "category": "Media",
        "description": "Bilder- und Fotoarchiv",
    },
    {
        "host_path": "/home/mb/Videos",
        "container_path": "/opt/data/videos",
        "rw": True,
        "label": "Videos",
        "category": "Media",
        "description": "Video- und Multimedia-Ordner",
    },
    {
        "host_path": "/media/work-data",
        "container_path": "/opt/data/work-data",
        "rw": True,
        "label": "Arbeitsdateien (work-data)",
        "category": "Storage Root",
        "description": "Zentrale Arbeitsdaten-Partition",
    },
    {
        "host_path": "/media/privat-data/10_PrivatBüro",
        "container_path": "/opt/data/privat-buero",
        "rw": True,
        "label": "PrivatBüro (Archiv & Steuern)",
        "category": "Storage Root",
        "description": "Archivierte Dokumente, Verträge und Steuerunterlagen",
    },
    {
        "host_path": "/media/xchg/ai-agents-workspaces",
        "container_path": "/opt/data/agents-workspaces",
        "rw": True,
        "label": "Agents Workspaces",
        "category": "Shared AI",
        "description": "Geteilter Arbeitsbereich der KI-Agenten",
    },
    {
        "host_path": "/media/xchg/ai-knowledge-base",
        "container_path": "/opt/data/knowledge-base",
        "rw": True,
        "label": "Obsidian AI Knowledge Base",
        "category": "Shared AI",
        "description": "Obsidian-Vault und Dokumentations-Wurzel",
    },
    {
        "host_path": "/media/xchg/ai-graph",
        "container_path": "/opt/data/graph-data",
        "rw": True,
        "label": "Graph Database",
        "category": "Shared AI",
        "description": "Persistente Wissensgraph-Daten",
    },
    {
        "host_path": "/media/xchg/ai-tools-data",
        "container_path": "/opt/data/tools-data",
        "rw": True,
        "label": "AI Tools & MCP Data",
        "category": "Shared AI",
        "description": "Werkzeugdaten, Docker-Runtime und MCP-Ressourcen",
    },
    {
        "host_path": "/home/mb/scripts",
        "container_path": "/opt/data/scripts",
        "rw": True,
        "label": "Scripts",
        "category": "Scripts",
        "description": "Automatisierungs- und System-Skripte",
    },
    {
        "host_path": "/media/xchg/jules-mcp-server",
        "container_path": "/opt/data/jules-mcp-server",
        "rw": False,
        "label": "Jules MCP Server (Schreibgeschützt)",
        "category": "MCP Server",
        "description": "Jules MCP Server (nur Lesezugriff im Container)",
    },
    {
        "host_path": "/media/xchg/ai-agents-workspaces/hermes/.hermes",
        "container_path": "/opt/data",
        "rw": True,
        "label": "Hermes Basisdaten (.hermes)",
        "category": "Hermes Internal",
        "description": "Hermes Agent Konfiguration, Plugins und SQLite DBs",
    },
]


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)


class _UnixHTTPHandler(urllib.request.AbstractHTTPHandler):
    def __init__(self, socket_path: str):
        super().__init__()
        self.socket_path = socket_path

    def unix_open(self, req):
        return self.do_open(lambda host: _UnixHTTPConnection(self.socket_path), req)


class DockerMountService:
    """Discovers and inspects container mounts and translates file paths."""

    def __init__(self, docker_socket_path: str = "/var/run/docker.sock"):
        self.docker_socket_path = docker_socket_path
        self._cached_mounts: Optional[List[Dict[str, Any]]] = None
        self._is_in_container = os.path.exists("/.dockerenv") or os.path.exists("/opt/hermes")

    def is_in_container(self) -> bool:
        """Returns True if the current process is running inside the Docker container."""
        return self._is_in_container

    def get_mounts(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Returns all discovered mount points with real-time accessibility,
        read/write permissions, and disk space usage.
        """
        if self._cached_mounts is not None and not force_refresh:
            return self._cached_mounts

        discovered_mounts: List[Dict[str, Any]] = []

        # 1. Try querying Docker socket
        if os.path.exists(self.docker_socket_path):
            try:
                opener = urllib.request.build_opener(_UnixHTTPHandler(self.docker_socket_path))
                # Probe hermes-dashboard or inspect container
                target_container = os.getenv("HOSTNAME", "hermes-dashboard")
                url = f"unix://localhost/containers/{target_container}/json"
                req = urllib.request.Request(url)
                with opener.open(req, timeout=1.5) as resp:
                    cdata = json.loads(resp.read().decode("utf-8"))
                    raw_mounts = cdata.get("Mounts", [])
                    for m in raw_mounts:
                        src = m.get("Source", "")
                        dst = m.get("Destination", "")
                        if dst in ("/var/run/docker.sock", "/run/docker.sock", "/mcp"):
                            continue
                        
                        match_known = next(
                            (k for k in KNOWN_HERMES_MOUNTS if k["container_path"] == dst or k["host_path"] == src),
                            None
                        )
                        label = match_known["label"] if match_known else Path(dst).name.capitalize()
                        cat = match_known["category"] if match_known else "Custom Mount"
                        desc = match_known["description"] if match_known else f"Mount {src} -> {dst}"

                        discovered_mounts.append({
                            "host_path": src,
                            "container_path": dst,
                            "rw": bool(m.get("RW", True)),
                            "label": label,
                            "category": cat,
                            "description": desc,
                        })
            except Exception as exc:
                logger.debug("Could not query docker socket %s: %s", self.docker_socket_path, exc)

        # 2. Fallback to KNOWN_HERMES_MOUNTS if socket query did not yield mounts
        if not discovered_mounts:
            discovered_mounts = [dict(m) for m in KNOWN_HERMES_MOUNTS]

        # 3. Enrich each mount with live accessibility and disk usage
        enriched: List[Dict[str, Any]] = []
        for m in discovered_mounts:
            cpath = m["container_path"]
            hpath = m["host_path"]

            active_path = cpath if self._is_in_container else hpath
            exists = os.path.exists(active_path)
            
            is_writable = False
            total_gb = 0.0
            free_gb = 0.0
            used_percent = 0.0

            if exists:
                try:
                    usage = shutil.disk_usage(active_path)
                    total_gb = round(usage.total / (1024 ** 3), 1)
                    free_gb = round(usage.free / (1024 ** 3), 1)
                    used_percent = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0.0
                    is_writable = m.get("rw", True) and os.access(active_path, os.W_OK)
                except Exception:
                    is_writable = m.get("rw", True)
            else:
                if os.path.exists(hpath):
                    try:
                        usage = shutil.disk_usage(hpath)
                        total_gb = round(usage.total / (1024 ** 3), 1)
                        free_gb = round(usage.free / (1024 ** 3), 1)
                        used_percent = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0.0
                        is_writable = m.get("rw", True) and os.access(hpath, os.W_OK)
                    except Exception:
                        is_writable = m.get("rw", True)

            enriched.append({
                "host_path": hpath,
                "container_path": cpath,
                "rw": m.get("rw", True),
                "is_writable": is_writable,
                "accessible": exists or os.path.exists(hpath),
                "label": m.get("label", Path(cpath).name),
                "category": m.get("category", "General"),
                "description": m.get("description", ""),
                "total_gb": total_gb,
                "free_gb": free_gb,
                "used_percent": used_percent,
            })

        cat_priority = {"Dumpzone": 0, "Storage Root": 1, "Host Work": 2, "Media": 3, "Shared AI": 4}
        enriched.sort(key=lambda x: (cat_priority.get(x["category"], 9), x["label"]))

        self._cached_mounts = enriched
        return enriched

    def translate_to_container_path(self, path_str: str) -> Optional[str]:
        """
        Translates a host path to its corresponding container path.
        If already a valid container path, returns it unchanged.
        If unmounted, returns None.
        """
        norm_path = os.path.abspath(path_str)
        mounts = self.get_mounts()

        if norm_path.startswith("/opt/data") or norm_path == "/opt/data":
            return norm_path

        best_match: Optional[Dict[str, Any]] = None
        best_prefix_len = -1

        for m in mounts:
            hpath = m["host_path"]
            if norm_path == hpath or norm_path.startswith(hpath + "/"):
                if len(hpath) > best_prefix_len:
                    best_prefix_len = len(hpath)
                    best_match = m

        if best_match:
            rel = os.path.relpath(norm_path, best_match["host_path"])
            c_base = best_match["container_path"]
            if rel == ".":
                return c_base
            return os.path.normpath(os.path.join(c_base, rel))

        return None

    def translate_to_host_path(self, path_str: str) -> Optional[str]:
        """
        Translates a container path to its host path.
        If already a host path, returns it unchanged if it matches a mount.
        """
        norm_path = os.path.abspath(path_str)
        mounts = self.get_mounts()

        if norm_path.startswith("/opt/data") or norm_path == "/opt/data":
            best_match: Optional[Dict[str, Any]] = None
            best_prefix_len = -1
            for m in mounts:
                cpath = m["container_path"]
                if norm_path == cpath or norm_path.startswith(cpath + "/"):
                    if len(cpath) > best_prefix_len:
                        best_prefix_len = len(cpath)
                        best_match = m

            if best_match:
                rel = os.path.relpath(norm_path, best_match["container_path"])
                h_base = best_match["host_path"]
                if rel == ".":
                    return h_base
                return os.path.normpath(os.path.join(h_base, rel))
            return None

        for m in mounts:
            hpath = m["host_path"]
            if norm_path == hpath or norm_path.startswith(hpath + "/"):
                return norm_path

        return None

    def validate_destination_path(self, path_str: str) -> Dict[str, Any]:
        """
        Validates whether a proposed destination path is mounted inside the
        Hermes container and has write permissions.
        """
        mounts = self.get_mounts()
        cpath = self.translate_to_container_path(path_str)
        hpath = self.translate_to_host_path(path_str)

        if not cpath:
            return {
                "valid": False,
                "is_mounted": False,
                "is_writable": False,
                "container_path": None,
                "host_path": path_str,
                "message": (
                    f"Pfad '{path_str}' liegt außerhalb der gemounteten Docker-Verzeichnisse! "
                    "Hermes hat in der Container-Umgebung keinen Zugriff darauf."
                ),
                "mount": None,
            }

        matched_mount = None
        best_len = -1
        for m in mounts:
            mp = m["container_path"]
            if cpath == mp or cpath.startswith(mp + "/"):
                if len(mp) > best_len:
                    best_len = len(mp)
                    matched_mount = m

        if not matched_mount:
            return {
                "valid": False,
                "is_mounted": False,
                "is_writable": False,
                "container_path": cpath,
                "host_path": hpath or path_str,
                "message": f"Kein passender Docker-Mount für '{path_str}' gefunden.",
                "mount": None,
            }

        if not matched_mount.get("rw", True):
            return {
                "valid": False,
                "is_mounted": True,
                "is_writable": False,
                "container_path": cpath,
                "host_path": matched_mount["host_path"],
                "message": f"Verzeichnis '{matched_mount['label']}' ist im Container schreibgeschützt (ro)!",
                "mount": matched_mount,
            }

        return {
            "valid": True,
            "is_mounted": True,
            "is_writable": True,
            "container_path": cpath,
            "host_path": hpath or matched_mount["host_path"],
            "message": f"Gültig: Gemountet in '{matched_mount['label']}' ({matched_mount.get('free_gb', 0)} GB frei)",
            "mount": matched_mount,
        }


# Singleton instance
docker_mount_service = DockerMountService()
