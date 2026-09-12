"""
SSH Node Inspector Adapter.
Implements SSHNodePort: manages remote SSH execution, dynamic LAN IP discovery,
storage mount telemetry, Docker container inspection, and remote directory profiling.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from hermes_auto_organizer.application.ports.ssh_node_port import SSHNodePort

logger = logging.getLogger("hermes.storage.ssh_node_inspector")


class SSHNodeInspector(SSHNodePort):
    """Inspects remote LAN machines over SSH with automatic host resolution and caching."""

    DEFAULT_NODE_CONFIGS: Dict[str, Dict[str, Any]] = {
        "debian1": {
            "name": "kimi-debian1",
            "role": "Server Node & Compute Hub",
            "user": "mb",
            "candidate_hosts": ["192.168.178.89", "debian1", "192.168.178.111"],
            "key_name": "id_ed25519_debian1",
            "port": 22,
        }
    }

    @classmethod
    def _find_key_path(cls, key_name: str = "id_ed25519_debian1") -> Optional[str]:
        candidates = [
            Path.home() / ".ssh" / key_name,
            Path("/opt/data/.ssh") / key_name,
            Path("/home/mb/.ssh") / key_name,
            Path("/media/xchg/ai-agents-workspaces/hermes/.hermes/.ssh") / key_name,
        ]
        for p in candidates:
            try:
                if p.exists() and p.is_file():
                    return str(p)
            except OSError:
                pass
        return None

    def __init__(self, node_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self._configs = dict(self.DEFAULT_NODE_CONFIGS)
        if node_configs:
            self._configs.update(node_configs)
        # Cache for resolved active hosts: {node_id: (resolved_ip, timestamp)}
        self._host_cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl_seconds = 300.0  # 5 minutes

    def resolve_active_host(self, node_id: str = "debian1") -> Optional[str]:
        """Dynamically finds the currently reachable IP/hostname for the remote node."""
        cfg = self._configs.get(node_id)
        if not cfg:
            return None

        # Check valid cached host
        if node_id in self._host_cache:
            cached_host, cached_at = self._host_cache[node_id]
            if time.time() - cached_at < self._cache_ttl_seconds:
                return cached_host

        # Probe candidate hosts
        candidates = cfg.get("candidate_hosts", [])
        key_name = cfg.get("key_name", "id_ed25519_debian1")
        key_path = cfg.get("key_path") or self._find_key_path(key_name)
        user = cfg.get("user", "mb")
        port = cfg.get("port", 22)

        for host in candidates:
            cmd = [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=2",
                "-o", "StrictHostKeyChecking=no",
                "-p", str(port),
            ]
            if key_path and Path(key_path).exists():
                cmd.extend(["-i", key_path])
            cmd.extend([f"{user}@{host}", "echo SSH_PING_OK"])

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if proc.returncode == 0 and "SSH_PING_OK" in proc.stdout:
                    self._host_cache[node_id] = (host, time.time())
                    logger.info("Resolved active SSH host for '%s': %s", node_id, host)
                    return host
            except (subprocess.TimeoutExpired, OSError) as exc:
                logger.debug("Candidate %s for %s unreachable: %s", host, node_id, exc)

        return None

    def execute_remote(
        self,
        node_id: str,
        command: str,
        timeout: int = 8,
    ) -> Tuple[bool, str, float]:
        """Executes a bash command on the remote node and measures roundtrip latency."""
        host = self.resolve_active_host(node_id)
        if not host:
            return False, f"Host for node '{node_id}' could not be resolved or is offline.", 0.0

        cfg = self._configs.get(node_id, {})
        key_name = cfg.get("key_name", "id_ed25519_debian1")
        key_path = cfg.get("key_path") or self._find_key_path(key_name)
        user = cfg.get("user", "mb")
        port = cfg.get("port", 22)

        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=4",
            "-o", "StrictHostKeyChecking=no",
            "-p", str(port),
        ]
        if key_path and Path(key_path).exists():
            cmd.extend(["-i", key_path])
        cmd.extend([f"{user}@{host}", command])

        t0 = time.time()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            latency_ms = round((time.time() - t0) * 1000, 1)
            if proc.returncode == 0:
                return True, proc.stdout, latency_ms
            return False, proc.stderr or proc.stdout, latency_ms
        except subprocess.TimeoutExpired:
            return False, f"SSH command timed out after {timeout}s", round((time.time() - t0) * 1000, 1)
        except OSError as exc:
            return False, f"SSH execution error: {exc}", round((time.time() - t0) * 1000, 1)

    def test_connection(self, node_id: str = "debian1") -> Dict[str, Any]:
        """Test SSH connectivity, measure latency, and retrieve basic telemetry."""
        success, out, latency = self.execute_remote(
            node_id,
            "hostname && uptime && uname -r",
            timeout=5,
        )
        if not success:
            return {
                "ok": False,
                "node_id": node_id,
                "is_online": False,
                "error": out,
            }

        lines = [line.strip() for line in out.splitlines() if line.strip()]
        hostname = lines[0] if len(lines) > 0 else "unknown"
        uptime_str = lines[1] if len(lines) > 1 else ""
        kernel = lines[2] if len(lines) > 2 else ""
        resolved_host = self.resolve_active_host(node_id)

        return {
            "ok": True,
            "node_id": node_id,
            "is_online": True,
            "host": resolved_host,
            "hostname": hostname,
            "uptime": uptime_str,
            "kernel": kernel,
            "latency_ms": latency,
        }

    def get_node_status(self, node_id: str = "debian1") -> Dict[str, Any]:
        """Retrieve rich system telemetry from remote node."""
        py_script = (
            "import os, sys, json, shutil\n"
            "load1, load5, load15 = os.getloadavg() if hasattr(os, 'getloadavg') else (0,0,0)\n"
            "mem_total = mem_avail = 0\n"
            "try:\n"
            "    with open('/proc/meminfo') as f:\n"
            "        for l in f:\n"
            "            if l.startswith('MemTotal:'): mem_total = int(l.split()[1]) * 1024\n"
            "            elif l.startswith('MemAvailable:'): mem_avail = int(l.split()[1]) * 1024\n"
            "except Exception: pass\n"
            "print(json.dumps({\n"
            "    'load_avg': [round(load1, 2), round(load5, 2), round(load15, 2)],\n"
            "    'mem_total_bytes': mem_total,\n"
            "    'mem_avail_bytes': mem_avail,\n"
            "    'mem_used_pct': round((1 - (mem_avail / max(1, mem_total))) * 100, 1)\n"
            "}))\n"
        )
        success, out, latency = self.execute_remote(node_id, f"python3 -c {subprocess.list2cmdline([py_script])}")
        if not success:
            return {"ok": False, "node_id": node_id, "error": out}

        try:
            data = json.loads(out.strip())
            data.update({"ok": True, "node_id": node_id, "latency_ms": latency})
            return data
        except json.JSONDecodeError as exc:
            return {"ok": False, "node_id": node_id, "error": f"Failed to parse JSON: {exc}"}

    def get_node_mounts(self, node_id: str = "debian1") -> List[Dict[str, Any]]:
        """Retrieve mounted storage partitions, sizes, and free space on the remote host."""
        success, out, _ = self.execute_remote(node_id, "df -B1 -T -x tmpfs -x devtmpfs -x overlay")
        if not success:
            logger.warning("Failed to retrieve mounts for %s: %s", node_id, out)
            return []

        mounts: List[Dict[str, Any]] = []
        lines = out.strip().splitlines()
        if len(lines) <= 1:
            return []

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 7:
                fs, fstype, total, used, avail, pcent, mpoint = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
                try:
                    total_b = int(total)
                    used_b = int(used)
                    avail_b = int(avail)
                    pct = float(pcent.rstrip("%"))
                except ValueError:
                    continue

                mounts.append({
                    "filesystem": fs,
                    "fstype": fstype,
                    "total_bytes": total_b,
                    "used_bytes": used_b,
                    "available_bytes": avail_b,
                    "used_percent": pct,
                    "mounted_on": mpoint,
                    "is_shared_pool": "sdc2" in fs or "xchg" in mpoint,
                    "is_cold_backup": "ext10tb" in mpoint,
                })

        return mounts

    def get_node_docker_services(self, node_id: str = "debian1") -> List[Dict[str, Any]]:
        """Retrieve active Docker containers running on the remote node."""
        cmd = "docker ps -a --format '{{json .}}' 2>/dev/null || true"
        success, out, _ = self.execute_remote(node_id, cmd)
        if not success or not out.strip():
            return []

        services: List[Dict[str, Any]] = []
        for line in out.strip().splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                c = json.loads(line)
                services.append({
                    "id": c.get("ID", "")[:12],
                    "name": c.get("Names", ""),
                    "image": c.get("Image", ""),
                    "status": c.get("Status", ""),
                    "state": c.get("State", "running"),
                    "ports": c.get("Ports", ""),
                    "is_database": "postgres" in c.get("Names", "").lower() or "pg" in c.get("Names", "").lower(),
                    "is_mcp": "mcp-" in c.get("Names", "").lower(),
                })
            except json.JSONDecodeError:
                continue

        return services

    def profile_remote_directory(
        self,
        node_id: str = "debian1",
        remote_path: str = "/media/sdc2-2tb-work-privat-xchg",
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Performs fast directory profiling on the remote machine via Python."""
        py_script = (
            "import os, sys, json, math\n"
            "from pathlib import Path\n"
            "from collections import Counter\n"
            f"root = Path('{remote_path}')\n"
            "if not root.exists():\n"
            "    print(json.dumps({'error': 'Path does not exist'}))\n"
            "    sys.exit(0)\n"
            "direct_files = 0\n"
            "direct_bytes = 0\n"
            "subdirs = []\n"
            "exts = Counter()\n"
            "sample_files = []\n"
            "try:\n"
            "    for entry in os.scandir(str(root)):\n"
            "        try:\n"
            "            if entry.is_file(follow_symlinks=False):\n"
            "                direct_files += 1\n"
            "                st = entry.stat()\n"
            "                direct_bytes += st.st_size\n"
            "                ext = Path(entry.name).suffix.lower()\n"
            "                exts[ext] += 1\n"
            "                if len(sample_files) < 5 and not entry.name.startswith('.'):\n"
            "                    sample_files.append({'name': entry.name, 'size': st.st_size, 'ext': ext})\n"
            "            elif entry.is_dir(follow_symlinks=False):\n"
            "                subdirs.append(entry.name)\n"
            "        except Exception:\n"
            "            continue\n"
            "except Exception as e:\n"
            "    print(json.dumps({'error': str(e)}))\n"
            "    sys.exit(0)\n"
            "print(json.dumps({\n"
            "    'path': str(root),\n"
            "    'direct_files_count': direct_files,\n"
            "    'direct_bytes': direct_bytes,\n"
            "    'subdirs_count': len(subdirs),\n"
            "    'subdirs': subdirs[:15],\n"
            "    'dominant_extension': exts.most_common(1)[0][0] if exts else '',\n"
            "    'sample_files': sample_files\n"
            "}))\n"
        )

        success, out, latency = self.execute_remote(
            node_id,
            f"python3 -c {subprocess.list2cmdline([py_script])}",
            timeout=10,
        )
        if not success:
            return {"ok": False, "path": remote_path, "error": out}

        try:
            res = json.loads(out.strip())
            res.update({"ok": True, "node_id": node_id, "latency_ms": latency})
            return res
        except json.JSONDecodeError as exc:
            return {"ok": False, "path": remote_path, "error": f"Failed to parse JSON: {exc}"}
