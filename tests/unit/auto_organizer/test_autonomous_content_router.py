"""
Unit tests for FolderPurposeDistiller and AutonomousContentRouter.

Verifies:
1. Autonomous distillation of folder purposes from existing file contents.
2. Content-driven routing of unorganized files to existing folders (Yellow proposals).
3. Explicit proposal of new folder creation when no existing folder matches.
4. Human-readable abstract explanations of the filesystem.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from hermes_auto_organizer.application.services.autonomous_content_router import (
    AutonomousContentRouter,
    _cosine_similarity,
)
from hermes_auto_organizer.application.services.folder_purpose_distiller import (
    FolderPurposeDistiller,
)
from hermes_auto_organizer.domain.models import (
    FileEmbedding,
    FileExtraction,
    FileNode,
    RuleState,
    SyncStatus,
)


def _make_node(path: str, name: str, ext: str, sha: str) -> FileNode:
    return FileNode(
        id=uuid4(),
        root_id=uuid4(),
        relative_path=f"rel/{name}",
        physical_path=path,
        file_name=name,
        file_extension=ext,
        size_bytes=1024,
        content_sha256=sha,
        mtime=datetime(2025, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
        is_deleted=False,
        sync_status=SyncStatus.CLEAN,
    )


def test_cosine_similarity_basic():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert _cosine_similarity(v1, v2) == pytest.approx(1.0)

    v3 = [0.0, 1.0, 0.0]
    assert _cosine_similarity(v1, v3) == pytest.approx(0.0)

    # Empty or mismatched
    assert _cosine_similarity([], [1.0]) == 0.0
    assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_folder_purpose_distiller_extracts_abstract_profile():
    # Existing files in an invoices folder
    n1 = _make_node("/media/work/invoices/telekom_jan.pdf", "telekom_jan.pdf", ".pdf", "sha_t1")
    n2 = _make_node("/media/work/invoices/vodafone_feb.pdf", "vodafone_feb.pdf", ".pdf", "sha_v1")

    # Extractions for existing files
    ext1 = FileExtraction(
        content_sha256="sha_t1",
        extraction_strategy="doc_parser",
        summary_text="Telekom Rechnung Januar 2025 mit USt und IBAN",
        metadata_json={
            "document_type": "rechnung",
            "entities": {"partner": "Telekom", "type": "Monatsrechnung"},
            "keywords": ["rechnung", "telekom", "telefonie", "ust-idnr"],
        },
    )
    ext2 = FileExtraction(
        content_sha256="sha_v1",
        extraction_strategy="doc_parser",
        summary_text="Vodafone Monatsrechnung für Internetanschluss",
        metadata_json={
            "document_type": "rechnung",
            "entities": {"partner": "Vodafone", "type": "Internet"},
            "keywords": ["rechnung", "vodafone", "dsl", "ust-idnr"],
        },
    )

    # Embeddings for existing files
    emb1 = FileEmbedding(content_sha256="sha_t1", embedding=[0.5, 0.5, 0.0])
    emb2 = FileEmbedding(content_sha256="sha_v1", embedding=[0.5, 0.3, 0.0])

    purposes = FolderPurposeDistiller.distill_from_data(
        nodes=[n1, n2],
        extractions_by_hash={"sha_t1": ext1, "sha_v1": ext2},
        embeddings_by_hash={"sha_t1": emb1, "sha_v1": emb2},
    )

    assert "/media/work/invoices" in purposes
    purpose = purposes["/media/work/invoices"]
    assert purpose.file_count == 2
    assert "rechnung" in purpose.document_types
    assert any("Telekom" in ent or "Vodafone" in ent for ent in purpose.characteristic_entities)
    assert ".pdf" in purpose.common_extensions
    assert len(purpose.embedding_centroid) == 3
    assert purpose.embedding_centroid[0] == pytest.approx(0.5)
    # Check abstract summary explains purpose to user
    assert "Rechnung" in purpose.purpose_summary


def test_autonomous_content_router_routes_to_matching_folder():
    # 1. Distilled folder purpose
    distiller_result = FolderPurposeDistiller.distill_from_data(
        nodes=[
            _make_node("/media/work-data/Rechnungen/rec1.pdf", "rec1.pdf", ".pdf", "sha_ex1"),
            _make_node("/media/work-data/Rechnungen/rec2.pdf", "rec2.pdf", ".pdf", "sha_ex2"),
        ],
        extractions_by_hash={
            "sha_ex1": FileExtraction(
                content_sha256="sha_ex1",
                extraction_strategy="doc_parser",
                summary_text="Rechnung Telekom",
                metadata_json={"document_type": "rechnung", "entities": ["Telekom"]},
            ),
            "sha_ex2": FileExtraction(
                content_sha256="sha_ex2",
                extraction_strategy="doc_parser",
                summary_text="Rechnung Vodafone",
                metadata_json={"document_type": "rechnung", "entities": ["Vodafone"]},
            ),
        },
    )

    # 2. Unorganized file in downloads: SCAN_0815.pdf (content is a Telekom invoice)
    unorg_node = _make_node("/home/mb/Downloads/SCAN_0815.pdf", "SCAN_0815.pdf", ".pdf", "sha_unorg")
    unorg_ext = FileExtraction(
        content_sha256="sha_unorg",
        extraction_strategy="ocr",
        summary_text="Eingehende Telekom Mobilfunk Rechnung mit Rechnungsbetrag",
        metadata_json={
            "document_type": "rechnung",
            "entities": {"partner": "Telekom"},
        },
    )

    router = AutonomousContentRouter(min_match_confidence=0.50)
    proposals = router.propose_routing(
        unorganized_nodes=[unorg_node],
        distilled_purposes=distiller_result,
        extractions_by_hash={"sha_unorg": unorg_ext},
    )

    assert len(proposals) == 1
    p = proposals[0]
    assert p.file_name == "SCAN_0815.pdf"
    assert p.suggested_target_folder == "/media/work-data/Rechnungen/"
    assert p.is_new_folder is False
    assert p.confidence >= 0.60
    assert p.state == RuleState.DRAFT  # Yellow 🟡 proposal waiting for user admission
    assert "Rechnungen" in p.explanation
    assert "Telekom" in p.explanation


def test_autonomous_content_router_proposes_new_folder_when_no_match():
    # 1. Distilled folder purpose only knows invoices
    distiller_result = FolderPurposeDistiller.distill_from_data(
        nodes=[_make_node("/media/work/invoices/rec.pdf", "rec.pdf", ".pdf", "sha_rec")],
        extractions_by_hash={
            "sha_rec": FileExtraction(
                content_sha256="sha_rec",
                extraction_strategy="doc",
                summary_text="Rechnung",
                metadata_json={"document_type": "rechnung"},
            )
        },
    )

    # 2. Unorganized file is a CAD architectural blueprint (completely different purpose)
    cad_node = _make_node("/home/mb/Downloads/bauplan_halle.dxf", "bauplan_halle.dxf", ".dxf", "sha_cad")
    cad_ext = FileExtraction(
        content_sha256="sha_cad",
        extraction_strategy="cad_parser",
        summary_text="CAD Grundriss Halle 4 Werkstatt",
        metadata_json={
            "document_type": "cad",
            "entities": {"projekt": "Werkstatt_Halle4"},
        },
    )

    router = AutonomousContentRouter(min_match_confidence=0.60)
    proposals = router.propose_routing(
        unorganized_nodes=[cad_node],
        distilled_purposes=distiller_result,
        extractions_by_hash={"sha_cad": cad_ext},
        default_base_dir="/media/work-data",
    )

    assert len(proposals) == 1
    p = proposals[0]
    assert p.is_new_folder is True  # Proposes creating a new folder
    assert "CAD-Projekte" in p.suggested_target_folder
    assert p.state == RuleState.DRAFT  # Yellow 🟡 proposal asking user for permission
    assert "Kein vorhandener Ordner erfüllt den Zweck" in p.explanation
