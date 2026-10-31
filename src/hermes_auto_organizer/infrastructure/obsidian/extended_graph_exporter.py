"""
Obsidian Extended Graph Exporter for Hermes Auto-Organizer.

Generates structured Markdown notes for Obsidian's Extended Graph plugin:
- Frontmatter metadata (tags, node types, entropy, disruptions, status)
- Directed wikilinks between folders, parents, targets, and clusters
- Allows instant visual graph exploration without heavy WebGL code in the plugin

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import List, Optional

from hermes_auto_organizer.domain.profiler_models import (
    FolderProfile,
    NaturalLanguageRule,
    OutlierItem,
    TreeDiffNode,
)


def _sanitize_name(name: str) -> str:
    """Sanitizes filename for Obsidian markdown links."""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip() or "Unnamed"


class ObsidianExtendedGraphExporter:
    """Exports FolderProfile and TreeDiff into Obsidian Extended Graph notes."""

    def __init__(self, vault_path: Path | str) -> None:
        self.vault_path = Path(vault_path).resolve()
        self.output_dir = self.vault_path / "Auto-Organizer" / "Graph-Nodes"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_graph(
        self,
        root_profile: FolderProfile,
        diff_nodes: Optional[List[TreeDiffNode]] = None,
        outliers: Optional[List[OutlierItem]] = None,
    ) -> Path:
        """Exports the full folder tree as Obsidian notes ready for Extended Graph plugin."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Recursive export of nodes
        self._export_folder_node(root_profile, parent_note_name=None, diff_nodes=diff_nodes or [])

        # 2. Master Map note
        index_file = self.vault_path / "Auto-Organizer" / "🌳 Lan-Tree Graph Index.md"
        index_lines = [
            "---",
            "tags: [auto-organizer, extended-graph, lan-tree, index]",
            f"updated: {now_str}",
            f"root_path: \"{root_profile.path}\"",
            f"total_files: {root_profile.total_files_count}",
            f"mime_entropy: {root_profile.mime_entropy:.2f}",
            "---",
            "",
            f"# 🌳 LAN Storage Tree Graph Index",
            "",
            f"> Zuletzt analysiert: **{now_str}**",
            f"> Wurzelverzeichnis: `{root_profile.path}`",
            f"> Dateien erfasst: **{root_profile.total_files_count}** | Gesamtgröße: **{root_profile.total_bytes // (1024*1024)} MB**",
            "",
            "## 📍 Einstiegspunkt",
            f"- [[{_sanitize_name(root_profile.name)}]]",
            "",
            "## ⚠️ Erkannte Anomalien & Ausreißer",
        ]

        if outliers:
            for out in outliers:
                index_lines.append(
                    f"- **{out.disruption_type.value}**: `{out.source_path}` ➔ Ziel: `{out.proposal.target_path}` ({out.reason_de})"
                )
        else:
            index_lines.append("- Keine offenen Anomalien erkannt.")

        index_lines.extend([
            "",
            "---",
            "*Tipp: Öffne den Obsidian Graph View oder das 'Extended Graph' Plugin, um die farbigen Knoten und Verknüpfungen zu betrachten.*",
        ])

        index_file.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        return index_file

    def _export_folder_node(
        self,
        node: FolderProfile,
        parent_note_name: Optional[str],
        diff_nodes: List[TreeDiffNode],
    ) -> None:
        note_name = _sanitize_name(node.name)
        note_path = self.output_dir / f"{note_name}.md"

        # Check if this node has a move/reorganize action
        matched_diff = next((d for d in diff_nodes if d.source_path == node.path), None)
        action = matched_diff.action if matched_diff else "RETAIN"
        target_path = matched_diff.target_path if matched_diff else None

        disruption_tags = [f"disruption/{d.disruption_type.value.lower()}" for d in node.disruptions]
        status_tag = "status/disrupted" if node.disruptions else "status/clean"
        action_tag = f"action/{action.lower()}"

        tags = ["auto-organizer/node", status_tag, action_tag] + disruption_tags

        lines = [
            "---",
            f"title: \"{node.name}\"",
            "type: folder",
            f"path: \"{node.path}\"",
            f"depth: {node.depth}",
            f"files_count: {node.direct_files_count}",
            f"total_files: {node.total_files_count}",
            f"bytes: {node.total_bytes}",
            f"mime_entropy: {node.mime_entropy:.2f}",
            f"dominant_extension: \"{node.dominant_extension}\"",
            f"action: \"{action}\"",
        ]
        if target_path:
            lines.append(f"target_path: \"{target_path}\"")
        if parent_note_name:
            lines.append(f"parent: \"[[{parent_note_name}]]\"")

        lines.append("tags:")
        for t in tags:
            lines.append(f"  - {t}")
        lines.append("---")
        lines.append("")

        lines.append(f"# 📁 {node.name}")
        lines.append(f"> Pfad: `{node.path}` | Entropie: **{node.mime_entropy:.2f}** | Dateien: **{node.total_files_count}**")
        lines.append("")

        if node.disruptions:
            lines.append("## ⚠️ Auffälligkeiten")
            for d in node.disruptions:
                lines.append(f"- **{d.disruption_type.value}** ({d.severity.value}): {d.description}")
            lines.append("")

        lines.append("## 🔗 Beziehungen (Graph-Kanten)")
        if parent_note_name:
            lines.append(f"- Übergeordneter Ordner: [[{parent_note_name}]]")

        if node.subfolders:
            lines.append("- Unterordner:")
            for sub in node.subfolders:
                sub_name = _sanitize_name(sub.name)
                lines.append(f"  - [[{sub_name}]]")

        if target_path and action == "MOVE":
            target_clean = _sanitize_name(Path(target_path).name)
            lines.append(f"- ➔ Geplantes Reorganisationsziel: [[{target_clean}]]")

        note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Recurse for subfolders
        for sub in node.subfolders:
            self._export_folder_node(sub, parent_note_name=note_name, diff_nodes=diff_nodes)
