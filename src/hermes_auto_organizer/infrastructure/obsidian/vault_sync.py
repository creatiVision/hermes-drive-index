"""
Obsidian vault markdown exporter for Hermes Auto-Organizer.
Generates interactive dashboards, taxonomy trees, and move manifests.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from hermes_auto_organizer.domain.models import MoveIntent, StorageRoot, StructuralAnomaly


class ObsidianVaultVisualizer:
    """Renders structured Markdown files inside <vault>/Auto-Organizer/."""

    def __init__(self, vault_dir: Path) -> None:
        self._target_dir = vault_dir / "Auto-Organizer"
        self._target_dir.mkdir(parents=True, exist_ok=True)

    async def write_overview_report(
        self,
        roots: Sequence[StorageRoot],
        total_files: int,
        anomalies: Sequence[StructuralAnomaly],
    ) -> Path:
        """Render 📊 Current State Overview.md"""
        path = self._target_dir / "📊 Current State Overview.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "---",
            "tags: [auto-organizer, dashboard, storage-now-state]",
            f"updated: {now_str}",
            "---",
            "",
            "# Storage Now-State Overview",
            "",
            f"> Last updated: **{now_str}** | Total Files Tracked: **{total_files}**",
            "",
            "## 🗄️ Monitored Storage Roots",
            "",
            "| Root Name | Type | Path / URI | Watch Mode | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for root in roots:
            status_icon = "🟢 Active" if root.is_active else "⚪ Inactive"
            lines.append(
                f"| `{root.root_name}` | {root.root_type.value} | `{root.uri_path}` | {root.watch_mode.value} | {status_icon} |"
            )

        lines.extend([
            "",
            "## ⚠️ Flagged Anomalies & Dump Zones",
            "",
            f"Total Open Anomalies: **{len(anomalies)}**",
            "",
            "| Type | Confidence | Explanation | Recommended Action |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for anomaly in anomalies[:20]:
            lines.append(
                f"| `{anomaly.anomaly_type.value}` | {anomaly.confidence:.2f} | {anomaly.explanation} | {anomaly.recommended_action or 'Review'} |"
            )

        content = "\n".join(lines) + "\n"
        path.write_text(content, encoding="utf-8")
        return path

    async def write_pending_manifest(self, batch_id: str, intents: Sequence[MoveIntent]) -> Path:
        """Render 📋 Pending Moves.md with interactive checklists."""
        path = self._target_dir / "📋 Pending Moves.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "---",
            "tags: [auto-organizer, manifest, pending-moves]",
            f"batch_id: {batch_id}",
            f"generated: {now_str}",
            "---",
            "",
            f"# Pending Moves Manifest — Batch #{batch_id[:8]}",
            "",
            "> [!IMPORTANT]",
            "> To approve individual moves, check the boxes below or instruct Hermes in chat:",
            f"> `hermes organizer execute --batch-id {batch_id}`",
            "",
            f"Total Operations: **{len(intents)}**",
            "",
        ]

        for intent in intents:
            xdev_badge = " *(Cross-Device EXDEV)*" if intent.is_cross_device else ""
            collision_badge = " *(Collision Avoidance Suffix)*" if intent.requires_collision_rename else ""
            lines.extend([
                f"- [ ] **MOVE**: `{intent.source_path}` ➔ `{intent.destination_path}`{xdev_badge}{collision_badge}",
                f"  - *Operation:* `{intent.operation_type.value}` | *Source Hash:* `{intent.source_sha256[:12]}...`",
                "",
            ])

        content = "\n".join(lines) + "\n"
        path.write_text(content, encoding="utf-8")
        return path

    async def write_taxonomy_map(self, taxonomy_tree: dict[str, list[str]]) -> Path:
        """Render 🗺️ Ideal Taxonomy Map.md with synthesized ontology."""
        path = self._target_dir / "🗺️ Ideal Taxonomy Map.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "---",
            "tags: [auto-organizer, taxonomy, ideal-tree]",
            f"generated: {now_str}",
            "---",
            "",
            "# Synthesized Ideal Tree Ontology (S_ideal)",
            "",
            f"> Generated: **{now_str}** via Vector Clustering & Historical Path Analysis",
            "",
            "## 🌳 Target Hierarchy",
            "",
        ]
        for category, items in taxonomy_tree.items():
            lines.append(f"### 📂 {category} ({len(items)} items)")
            for item in items[:15]:
                lines.append(f"- [[{item}]]")
            if len(items) > 15:
                lines.append(f"- *... and {len(items) - 15} more*")
            lines.append("")

        content = "\n".join(lines) + "\n"
        path.write_text(content, encoding="utf-8")
        return path
