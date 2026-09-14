"""
Application Service for Remote SSH Node Management & Telemetry.

Coordinates SSHNodePort adapters to provide multi-node LAN visibility,
mount monitoring, Docker container tracking, and remote directory profiling.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from hermes_auto_organizer.application.ports.ssh_node_port import SSHNodePort
from hermes_auto_organizer.infrastructure.storage.ssh_node_inspector import SSHNodeInspector

logger = logging.getLogger("hermes.use_cases.ssh_node_service")


class SSHNodeService:
    """Orchestrates remote SSH node telemetry and diagnostics across the LAN."""

    def __init__(self, inspector: Optional[SSHNodePort] = None) -> None:
        self._inspector = inspector or SSHNodeInspector()

    def get_nodes_summary(self) -> List[Dict[str, Any]]:
        """Returns connection overview of configured remote LAN nodes."""
        nodes = ["debian1"]
        results: List[Dict[str, Any]] = []

        for node_id in nodes:
            conn = self._inspector.test_connection(node_id)
            results.append({
                "node_id": node_id,
                "name": "kimi-debian1" if node_id == "debian1" else node_id,
                "role": "Server Node & Compute Hub",
                "is_online": conn.get("is_online", False),
                "host": conn.get("host", ""),
                "hostname": conn.get("hostname", ""),
                "uptime": conn.get("uptime", ""),
                "kernel": conn.get("kernel", ""),
                "latency_ms": conn.get("latency_ms", 0.0),
                "error": conn.get("error"),
            })

        return results

    def get_node_overview(self, node_id: str = "debian1") -> Dict[str, Any]:
        """Provides in-depth telemetry for a specific remote node (mounts, containers, system)."""
        conn = self._inspector.test_connection(node_id)
        if not conn.get("is_online"):
            return {
                "ok": False,
                "node_id": node_id,
                "is_online": False,
                "error": conn.get("error", "Host is unreachable"),
            }

        status = self._inspector.get_node_status(node_id)
        mounts = self._inspector.get_node_mounts(node_id)
        docker_services = self._inspector.get_node_docker_services(node_id)

        # Highlight important mounts
        shared_pool = next((m for m in mounts if m.get("is_shared_pool")), None)
        cold_backup = next((m for m in mounts if m.get("is_cold_backup")), None)

        return {
            "ok": True,
            "node_id": node_id,
            "is_online": True,
            "host": conn.get("host"),
            "hostname": conn.get("hostname"),
            "uptime": conn.get("uptime"),
            "kernel": conn.get("kernel"),
            "latency_ms": conn.get("latency_ms"),
            "load_avg": status.get("load_avg", []),
            "memory": {
                "total_bytes": status.get("mem_total_bytes", 0),
                "avail_bytes": status.get("mem_avail_bytes", 0),
                "used_pct": status.get("mem_used_pct", 0.0),
            },
            "mounts": mounts,
            "shared_pool_mount": shared_pool,
            "cold_backup_mount": cold_backup,
            "docker_services": docker_services,
            "active_containers_count": len([s for s in docker_services if "up" in s.get("status", "").lower()]),
        }

    def profile_remote_directory(
        self,
        node_id: str = "debian1",
        remote_path: str = "/media/sdc2-2tb-work-privat-xchg",
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Runs fast remote directory profiling on the remote machine."""
        return self._inspector.profile_remote_directory(
            node_id=node_id,
            remote_path=remote_path,
            max_depth=max_depth,
        )


# Singleton service instance
ssh_node_service = SSHNodeService()
