"""
Folder Purpose Distiller for Hermes Auto-Organizer.

Autonomous ontology induction service:
Inspects existing filesystem folders and the files already living inside them,
extracts and aggregates their content characteristics (document types, entities,
keywords, and embeddings), and distills an abstract explanation of each folder's
purpose.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import logging
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from hermes_auto_organizer.domain.models import (
    FileEmbedding,
    FileExtraction,
    FileNode,
    FolderPurpose,
)

logger = logging.getLogger("hermes_auto_organizer.services.folder_purpose_distiller")


class FolderPurposeDistiller:
    """Distills abstract purpose profiles from existing directories and their files."""

    @classmethod
    def distill_from_data(
        cls,
        nodes: Sequence[FileNode],
        extractions_by_hash: Mapping[str, FileExtraction] | None = None,
        embeddings_by_hash: Mapping[str, FileEmbedding] | None = None,
        min_files_per_folder: int = 1,
    ) -> dict[str, FolderPurpose]:
        """
        Distills FolderPurpose for each folder represented in the provided FileNodes.

        Args:
            nodes: The FileNode list from existing storage roots.
            extractions_by_hash: Mapping from content_sha256 to FileExtraction.
            embeddings_by_hash: Mapping from content_sha256 to FileEmbedding.
            min_files_per_folder: Minimum files required to profile a folder.

        Returns:
            Dictionary mapping normalized folder path to FolderPurpose.
        """
        extractions_map = extractions_by_hash or {}
        embeddings_map = embeddings_by_hash or {}

        # 1. Group nodes by directory
        folder_nodes: dict[str, list[FileNode]] = defaultdict(list)
        for node in nodes:
            if node.is_deleted:
                continue
            dir_path = os.path.dirname(node.physical_path) or os.path.dirname(node.relative_path)
            if not dir_path or dir_path == ".":
                continue
            folder_nodes[dir_path].append(node)

        folder_purposes: dict[str, FolderPurpose] = {}

        for folder_path, f_nodes in folder_nodes.items():
            if len(f_nodes) < min_files_per_folder:
                continue

            doc_type_counts: Counter[str] = Counter()
            entity_counts: Counter[str] = Counter()
            keyword_counts: Counter[str] = Counter()
            extension_counts: Counter[str] = Counter()
            vector_sum: list[float] | None = None
            vector_count = 0

            sample_names = [n.file_name for n in f_nodes[:5]]

            for node in f_nodes:
                ext = (node.file_extension or os.path.splitext(node.file_name)[1]).lower()
                if ext:
                    extension_counts[ext] += 1

                sha = node.content_sha256
                if not sha:
                    continue

                # Extraction metadata
                ext_data = extractions_map.get(sha)
                if ext_data:
                    meta = ext_data.metadata_json or {}
                    # Document types
                    doc_type = meta.get("document_type")
                    if doc_type and doc_type != "binary_or_empty":
                        doc_type_counts[str(doc_type).lower()] += 1

                    # Entities
                    entities = meta.get("entities")
                    if isinstance(entities, dict):
                        for k, v in entities.items():
                            if isinstance(v, str) and v.strip():
                                entity_counts[v.strip()] += 1
                    elif isinstance(entities, (list, tuple)):
                        for ent in entities:
                            if isinstance(ent, str) and ent.strip():
                                entity_counts[ent.strip()] += 1

                    # Keywords
                    keywords = meta.get("keywords")
                    if isinstance(keywords, (list, tuple)):
                        for kw in keywords:
                            if isinstance(kw, str) and kw.strip():
                                keyword_counts[kw.strip().lower()] += 1

                # Embeddings
                emb_data = embeddings_map.get(sha)
                if emb_data and emb_data.embedding:
                    vec = emb_data.embedding
                    if vector_sum is None:
                        vector_sum = [0.0] * len(vec)
                    if len(vec) == len(vector_sum):
                        for i, val in enumerate(vec):
                            vector_sum[i] += val
                        vector_count += 1

            # Compute centroid vector
            centroid: tuple[float, ...] = ()
            if vector_sum and vector_count > 0:
                centroid = tuple(v / vector_count for v in vector_sum)

            # Distill abstract explanation
            folder_name = os.path.basename(folder_path)
            common_exts = tuple(ext for ext, _ in extension_counts.most_common(5))
            top_doc_types = tuple(dt for dt, _ in doc_type_counts.most_common(4))
            top_entities = tuple(ent for ent, _ in entity_counts.most_common(6))
            top_keywords = tuple(kw for kw, _ in keyword_counts.most_common(8))

            purpose_summary = cls._synthesize_purpose_summary(
                folder_name=folder_name,
                doc_types=top_doc_types,
                entities=top_entities,
                common_exts=common_exts,
                file_count=len(f_nodes),
            )

            folder_purposes[folder_path] = FolderPurpose(
                folder_path=folder_path,
                purpose_summary=purpose_summary,
                file_count=len(f_nodes),
                document_types=top_doc_types,
                characteristic_entities=top_entities,
                keywords=top_keywords,
                common_extensions=common_exts,
                sample_file_names=tuple(sample_names),
                embedding_centroid=centroid,
            )

        return folder_purposes

    @classmethod
    def _synthesize_purpose_summary(
        cls,
        folder_name: str,
        doc_types: tuple[str, ...],
        entities: tuple[str, ...],
        common_exts: tuple[str, ...],
        file_count: int,
    ) -> str:
        """Synthesizes a human-readable abstract explanation of a folder's purpose."""
        # 1. If explicit document types exist from content analysis
        if doc_types:
            types_str = ", ".join(t.capitalize() for t in doc_types[:3])
            if entities:
                ent_str = ", ".join(entities[:3])
                return f"Ordner für {types_str} (u.a. bezogen auf {ent_str})."
            return f"Ordner für {types_str} ({file_count} vorhandene Dateien)."

        # 2. Derive from extensions and folder name heuristics
        lower_name = folder_name.lower()
        if any(e in common_exts for e in (".pdf", ".docx", ".xlsx", ".csv")):
            if "rechnung" in lower_name or "invoice" in lower_name or "beleg" in lower_name:
                return "Zweck: Eingehende/Ausgehende Rechnungsdokumente und Buchungsbelege."
            if "vertrag" in lower_name or "contract" in lower_name or "versicherung" in lower_name:
                return "Zweck: Verträge, Vereinbarungen und Versicherungspolicen."
            if "steuer" in lower_name or "finanzamt" in lower_name or "tax" in lower_name:
                return "Zweck: Steuerunterlagen, behördliche Nachweise und Jahresabschlüsse."
            return f"Zweck: Dokumentenarchiv ({', '.join(common_exts)})."

        if any(e in common_exts for e in (".py", ".ts", ".js", ".sh", ".json", ".yml")):
            return f"Zweck: Quellcode, Skripte und Projektdateien ({', '.join(common_exts)})."

        if any(e in common_exts for e in (".dxf", ".dwg", ".step")):
            return "Zweck: Technische Zeichnungen, CAD-Pläne und Bauteildaten."

        if any(e in common_exts for e in (".png", ".jpg", ".jpeg", ".svg", ".webp")):
            return f"Zweck: Mediendateien, Bildmaterial und Grafiken ({', '.join(common_exts)})."

        return f"Vorhandener Dateiordner '{folder_name}' ({file_count} Dateien, {', '.join(common_exts)})."
