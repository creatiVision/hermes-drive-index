"""
Autonomous Content Router for Hermes Auto-Organizer.

Content-driven routing engine:
Matches unorganized files against distilled folder purposes based on actual
document content, extracted entities, document classifications, and semantic
embeddings, rather than superficial filename regexes.

Formulates proposals (Yellow 🟡) for user admission (Green 🟢).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Mapping, Sequence
from uuid import uuid4

from hermes_auto_organizer.domain.models import (
    FileEmbedding,
    FileExtraction,
    FileNode,
    FolderPurpose,
    RoutingProposal,
    RuleState,
)

logger = logging.getLogger("hermes_auto_organizer.services.autonomous_content_router")


def _cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class AutonomousContentRouter:
    """Evaluates unorganized files against distilled folder purposes and creates proposals."""

    def __init__(
        self,
        min_match_confidence: float = 0.60,
    ) -> None:
        self.min_match_confidence = min_match_confidence

    def propose_routing(
        self,
        unorganized_nodes: Sequence[FileNode],
        distilled_purposes: Mapping[str, FolderPurpose],
        extractions_by_hash: Mapping[str, FileExtraction] | None = None,
        embeddings_by_hash: Mapping[str, FileEmbedding] | None = None,
        default_base_dir: str = "/media/work-data",
    ) -> list[RoutingProposal]:
        """
        Formulates autonomous routing proposals for unorganized files.

        For each file:
        - If an existing folder's purpose matches its content, proposes that folder.
        - If no existing folder matches, proposes creating a new folder and explains why.
        """
        extractions = extractions_by_hash or {}
        embeddings = embeddings_by_hash or {}
        proposals: list[RoutingProposal] = []

        for node in unorganized_nodes:
            if node.is_deleted:
                continue

            sha = node.content_sha256 or ""
            ext_data = extractions.get(sha)
            emb_data = embeddings.get(sha)

            meta = ext_data.metadata_json if ext_data else {}
            doc_type = meta.get("document_type", "").lower() if meta else ""
            file_entities = self._extract_entities(meta)
            file_vector = emb_data.embedding if emb_data else []

            best_folder_path: str | None = None
            best_score = 0.0
            best_reason = ""
            matched_entities: list[str] = []

            # Compare against all distilled folder purposes
            for folder_path, purpose in distilled_purposes.items():
                score, reason, common_ents = self._evaluate_fit(
                    node=node,
                    doc_type=doc_type,
                    file_entities=file_entities,
                    file_vector=file_vector,
                    purpose=purpose,
                )
                if score > best_score:
                    best_score = score
                    best_folder_path = folder_path
                    best_reason = reason
                    matched_entities = common_ents

            # Decision: Existing folder vs. New folder proposal
            if best_folder_path and best_score >= self.min_match_confidence:
                target_folder = best_folder_path.rstrip("/") + "/"
                explanation = (
                    f"Inhalt passt zu Zielordner '{os.path.basename(best_folder_path)}': "
                    f"{best_reason} ({purpose.purpose_summary})"
                )
                proposals.append(
                    RoutingProposal(
                        id=uuid4(),
                        file_id=node.id,
                        file_name=node.file_name,
                        source_path=node.physical_path,
                        suggested_target_folder=target_folder,
                        is_new_folder=False,
                        confidence=round(best_score, 2),
                        explanation=explanation,
                        state=RuleState.DRAFT,  # Yellow 🟡 proposal
                        matched_document_type=doc_type or None,
                        matched_entities=tuple(matched_entities),
                    )
                )
            else:
                # No existing folder fits: propose creating a new folder
                new_folder_rel = self._propose_new_folder_path(node, doc_type, file_entities)
                suggested_new_folder = os.path.join(default_base_dir, new_folder_rel).rstrip("/") + "/"
                explanation = (
                    f"Kein vorhandener Ordner erfüllt den Zweck für diesen Dateiinhalt "
                    f"(Typ: '{doc_type or 'unbekannt'}', Entitäten: {', '.join(file_entities[:3]) or 'keine'}). "
                    f"Schlage vor, neuen Ordner '{new_folder_rel}' anzulegen."
                )
                proposals.append(
                    RoutingProposal(
                        id=uuid4(),
                        file_id=node.id,
                        file_name=node.file_name,
                        source_path=node.physical_path,
                        suggested_target_folder=suggested_new_folder,
                        is_new_folder=True,
                        confidence=0.50,
                        explanation=explanation,
                        state=RuleState.DRAFT,  # Yellow 🟡 proposal (needs admission)
                        matched_document_type=doc_type or None,
                        matched_entities=tuple(file_entities[:4]),
                    )
                )

        return proposals

    def _evaluate_fit(
        self,
        node: FileNode,
        doc_type: str,
        file_entities: list[str],
        file_vector: list[float],
        purpose: FolderPurpose,
    ) -> tuple[float, str, list[str]]:
        """Computes content fit score between a file and a folder purpose."""
        score = 0.0
        reasons: list[str] = []
        matched_ents: list[str] = []

        # 1. Document Type Match (weight: 0.40)
        if doc_type and doc_type in purpose.document_types:
            score += 0.40
            reasons.append(f"Dokumenttyp '{doc_type}' stimmt überein")
        elif doc_type:
            # Check semantic category keywords in purpose summary
            if doc_type in purpose.purpose_summary.lower():
                score += 0.30
                reasons.append(f"Dokumenttyp '{doc_type}' passt zu Ordner-Zweck")

        # 2. Entity Overlap (weight: 0.35)
        if file_entities and purpose.characteristic_entities:
            common = set(file_entities) & set(purpose.characteristic_entities)
            if common:
                matched_ents = list(common)
                score += min(0.35, 0.20 + (0.05 * len(common)))
                reasons.append(f"Gemeinsame Entitäten: {', '.join(matched_ents[:3])}")

        # 3. Vector Embedding Similarity (weight: 0.25)
        if file_vector and purpose.embedding_centroid:
            sim = _cosine_similarity(file_vector, purpose.embedding_centroid)
            if sim > 0.70:
                score += (sim - 0.70) / 0.30 * 0.25
                reasons.append(f"Hohe semantische Vektorähnlichkeit ({sim:.2f})")

        # 4. Extension Match (weight: 0.10)
        ext = (node.file_extension or os.path.splitext(node.file_name)[1]).lower()
        if ext and ext in purpose.common_extensions:
            score += 0.10

        reason_str = "; ".join(reasons) if reasons else "Geringe Übereinstimmung"
        return min(1.0, score), reason_str, matched_ents

    def _extract_entities(self, meta: dict) -> list[str]:
        """Extracts string entities from metadata."""
        if not meta:
            return []
        entities = meta.get("entities")
        res: list[str] = []
        if isinstance(entities, dict):
            for v in entities.values():
                if isinstance(v, str) and v.strip():
                    res.append(v.strip())
        elif isinstance(entities, (list, tuple)):
            for v in entities:
                if isinstance(v, str) and v.strip():
                    res.append(v.strip())
        return res

    def _propose_new_folder_path(self, node: FileNode, doc_type: str, entities: list[str]) -> str:
        """Determines a logical proposed new folder structure when no existing folder fits."""
        entity_prefix = entities[0] if entities else "Sonstige"
        # Sanitize entity prefix for directory path
        clean_entity = "".join(c for c in entity_prefix if c.isalnum() or c in ("-", "_")).strip() or "Allgemein"

        if doc_type in ("invoice", "rechnung", "beleg"):
            return f"001_cv-bookaccount/{node.mtime.year}/Neue_Kategorie_{clean_entity}"
        elif doc_type in ("contract", "vertrag", "police"):
            return f"Verträge/{clean_entity}"
        elif doc_type in ("cad", "drawing", "zeichung"):
            return f"CAD-Projekte/{clean_entity}"
        else:
            ext = (node.file_extension or os.path.splitext(node.file_name)[1]).lstrip(".")
            return f"Ablage_Neu/{doc_type.capitalize() or ext.upper() or 'Diverses'}"
