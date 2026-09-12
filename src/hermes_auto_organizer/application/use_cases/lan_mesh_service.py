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
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_auto_organizer.application.ports.disk_analyzer_port import LanMeshPort
from hermes_auto_organizer.domain.models import LanDeviceNode

logger = logging.getLogger("hermes_auto_organizer.use_cases.lan_mesh")


class LanMeshUseCase:
    """Orchestrates network mesh inspection and root partition triage."""

    def __init__(self, mesh_adapter: LanMeshPort) -> None:
        self._adapter = mesh_adapter

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
