"""
Port interface for remote SSH node inspection and telemetry in the LAN.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class SSHNodePort(Protocol):
    """Contract for inspecting remote LAN nodes (e.g. debian1) via SSH."""

    def test_connection(self, node_id: str = "debian1") -> Dict[str, Any]:
        """Test SSH connectivity, measure latency, and retrieve host identity."""
        ...

    def get_node_status(self, node_id: str = "debian1") -> Dict[str, Any]:
        """Retrieve system telemetry (uptime, load average, kernel, memory)."""
        ...

    def get_node_mounts(self, node_id: str = "debian1") -> List[Dict[str, Any]]:
        """Retrieve mounted filesystems, sizes, and utilization on the remote node."""
        ...

    def get_node_docker_services(self, node_id: str = "debian1") -> List[Dict[str, Any]]:
        """Retrieve running Docker containers and port mappings on the remote node."""
        ...

    def profile_remote_directory(
        self,
        node_id: str = "debian1",
        remote_path: str = "/media/sdc2-2tb-work-privat-xchg",
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Perform remote directory analysis and retrieve file/subdir distributions."""
        ...

    def profile_remote_subtree(
        self,
        node_id: str = "debian1",
        remote_path: str = "/media/sdc2-2tb-work-privat-xchg",
        max_depth: int = 2,
        include_hidden: bool = False,
    ) -> Any:
        """Perform recursive subtree profiling on the remote node returning a FolderProfile."""
        ...

