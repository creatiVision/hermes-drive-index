"""
Unit tests for AI Semantic Enricher.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from hermes_auto_organizer.application.services.semantic_enricher import SemanticEnricher


def test_heuristic_enrichment_invoice():
    enricher = SemanticEnricher()
    text = "Telekom Deutschland GmbH Rechnung 2026 Rechnungsbetrag: 49,99 EUR Zahlungsziel: 15.02.2026"
    result = enricher._heuristic_enrich(text, "telekom_rechnung.pdf")

    assert result["document_type"] == "invoice"
    assert "Rechnung" in result["keywords"]
    assert "2026" in result["keywords"]
    assert "49,99 EUR" in result["entities"]["detected_amounts"]
    assert "telekom_rechnung.pdf" in result["summary"]


def test_heuristic_enrichment_contract():
    enricher = SemanticEnricher()
    text = "Mietvertrag und Vereinbarung über Gewerberäume. Unterschrift des Mieters vom 01.01.2025."
    result = enricher._heuristic_enrich(text, "mietvertrag.docx")

    assert result["document_type"] == "contract"
    assert "Vertrag" in result["keywords"]
    assert "2025" in result["keywords"]


def test_llm_enrichment_mock():
    enricher = SemanticEnricher(api_key="mock_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"summary": "Telekom Monatsrechnung für Internet", "keywords": ["Telekom", "Internet", "Glasfaser"], "document_type": "invoice", "entities": {"betrag": "50 EUR"}}'
                }
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(enricher.generate_summary_and_keywords("Rechnung Telekom...", "telekom.pdf"))

    assert result["summary"] == "Telekom Monatsrechnung für Internet"
    assert "Telekom" in result["keywords"]
    assert result["document_type"] == "invoice"
