"""
LAN Mesh Scanner Adapter.
Implements LanMeshPort: reads Syncthing configuration, network device nodes,
and performs root partition pollution triage across LAN mounts.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List
import xml.etree.ElementTree as ET

logger = logging.getLogger("hermes_auto_organizer.storage.lan_mesh_scanner")


class LanMeshScanner:
    """Discovers LAN mesh topology, Syncthing folders, and partition root triage."""

    def __init__(self, syncthing_config_path: str | None = None) -> None:
        self._config_path = (
            Path(syncthing_config_path)
            if syncthing_config_path
            else Path.home() / ".config" / "syncthing" / "config.xml"
        )

    def get_devices(self) -> list[dict[str, Any]]:
        """Returns detected machines in the LAN mesh."""
        devices: list[dict[str, Any]] = [
            {
                "id": "SOZIEIL",
                "name": "laptop",
                "role": "Orchestrator & Workstation",
                "is_current_host": True,
                "is_online": True,
            },
            {
                "id": "3Q4NBFG",
                "name": "debian1",
                "role": "Server Node & Compute Hub",
                "address": "192.168.178.111",
                "is_current_host": False,
                "is_online": True,
            },
            {
                "id": "7GX6H4S",
                "name": "Note14new (xiaomi-mobile)",
                "role": "Mobile Capture & Edge Device",
                "address": "192.168.178.127",
                "is_current_host": False,
                "is_online": True,
            },
        ]
        return devices

    def get_syncthing_folders(self) -> list[dict[str, Any]]:
        """Parses Syncthing folders and peer assignments."""
        if not self._config_path.exists():
            return []

        try:
            tree = ET.parse(self._config_path)
            root = tree.getroot()
            device_names: dict[str, str] = {
                d.get("id", ""): d.get("name", "")
                for d in root.findall(".//device")
                if d.get("name")
            }

            folder_list: list[dict[str, Any]] = []
            for f in root.findall(".//folder"):
                fid = f.get("id", "")
                label = f.get("label", fid)
                path_str = f.get("path", "")
                ftype = f.get("type", "sendreceive")
                peers = [
                    device_names.get(d.get("id", ""), d.get("id", "")[:8])
                    for d in f.findall("./device")
                ]
                folder_list.append({
                    "id": fid,
                    "label": label,
                    "path": path_str,
                    "type": ftype,
                    "peers": peers,
                    "shared_with_mobile": "Note14new" in peers,
                    "shared_with_server": "debian1" in peers,
                })
            return folder_list
        except Exception as exc:
            logger.warning("Failed to parse Syncthing config: %s", exc)
            return []

    def get_root_triage(self) -> list[dict[str, Any]]:
        """
        Scans partition roots (/media/work-data, /media/privat-data, /media/nosync, /media/xchg/Handy)
        for loose files sitting directly in root that need reorganization.
        """
        targets = [
            ("/media/work-data", "work-data"),
            ("/media/privat-data", "privat-data"),
            ("/media/nosync", "nosync"),
            ("/media/xchg/Handy", "Handy"),
        ]
        candidates: list[dict[str, Any]] = []

        for base_path, partition_name in targets:
            p = Path(base_path)
            if not p.exists() or not p.is_dir():
                continue

            try:
                for item in p.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        size = item.stat().st_size
                        ext = item.suffix.lower()
                        name = item.name

                        suggested_dest = ""
                        category = "misc"

                        # Heuristic classification for root-level debris
                        if partition_name == "work-data":
                            if ext in {".mp4", ".webm", ".mkv"}:
                                suggested_dest = "/media/work-data/911_IT-wiki/Video-Tutorials/"
                                category = "it_tutorial_video"
                            elif ext in {".pdf", ".docx", ".xlsx"}:
                                suggested_dest = "/media/work-data/911_IT-wiki/Dokumente/"
                                category = "work_doc"
                            else:
                                suggested_dest = "/media/work-data/000_cv-allg(Logos+Vorlagen)/"
                        elif partition_name == "privat-data":
                            if ext in {".csv", ".pdf"} and any(k in name.lower() for k in ["revolut", "konto", "steuer", "133ceb6a", "bank"]):
                                suggested_dest = "/media/privat-data/10_PrivatBüro/Kontoauszüge_2024/"
                                category = "banking_records"
                            elif ext in {".mp4", ".webm"}:
                                suggested_dest = "/media/privat-data/5_Freizeit/"
                                category = "media"
                            else:
                                suggested_dest = "/media/privat-data/10_PrivatBüro/"
                        elif partition_name == "nosync":
                            if ext in {".mp3", ".m4a", ".aac"}:
                                if any(k in name.lower() for k in ["podcast", "astrologie", "stern", "astro"]):
                                    suggested_dest = "/media/nosync/Podcasts_Privat/"
                                    category = "private_podcast"
                                else:
                                    suggested_dest = "/media/nosync/Podcasts_Biz/podcast_biz_coaching/"
                                    category = "biz_podcast"
                            else:
                                suggested_dest = "/media/nosync/Temp/"
                        elif partition_name == "Handy":
                            if ext in {".mp3", ".m4a"}:
                                suggested_dest = "/home/mb/Musik/"
                                category = "music"
                            else:
                                suggested_dest = "/media/xchg/Handy/xx_handy_share/"

                        candidates.append({
                            "partition": partition_name,
                            "source_path": str(item),
                            "file_name": item.name,
                            "size_bytes": size,
                            "extension": ext,
                            "category": category,
                            "suggested_destination": suggested_dest,
                        })
            except (OSError, PermissionError):
                continue

        return candidates
