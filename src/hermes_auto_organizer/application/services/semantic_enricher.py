"""
AI Semantic Enricher for Hermes Auto-Organizer.

Generates AI-powered content summaries, structured keyword tagging,
document type classification, and entity extraction for indexed files.
Stores semantic metadata and embeddings in PostgreSQL 16 (pgvector).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from hermes_auto_organizer.domain.models import FileEmbedding, FileExtraction

logger = logging.getLogger("hermes_auto_organizer.services.enricher")


class SemanticEnricher:
    """Uses LLM and NLP heuristics to generate summaries, keywords, and document tags."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "openai/gpt-4o-mini") -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1"
        self.model = model

    async def generate_summary_and_keywords(self, raw_text: str, file_name: str) -> Dict[str, Any]:
        """
        Generates a concise semantic summary, extracted keywords, and document type.
        Falls back to rule-based NLP extraction if LLM credentials are not configured.
        """
        clean_text = " ".join(raw_text.split())
        if not clean_text:
            return {
                "summary": f"Datei {file_name} ohne extrahierbaren Textinhalt.",
                "keywords": [Path(file_name).suffix.lstrip(".")],
                "document_type": "binary_or_empty",
                "entities": {},
            }

        # If LLM API key is present, invoke LLM for rich structured summary & tagging
        if self.api_key:
            try:
                import httpx

                prompt = (
                    f"Analysiere folgenden Text der Datei '{file_name}'.\n"
                    f"Erstelle ein JSON mit folgenden Feldern:\n"
                    f"- 'summary': Prägnante deutsche Inhaltszusammenfassung (1-2 Sätze)\n"
                    f"- 'keywords': Liste von 4-8 relevanten Schlagwörtern (z.B. Firma, Thema, Projekt)\n"
                    f"- 'document_type': Kategorie (z.B. Rechnung, Vertrag, Beleg, CAD-Zeichnung, Notiz, Bericht)\n"
                    f"- 'entities': Wichtige Entitäten wie Betrag, Datum, Rechnungsnummer, Partner\n\n"
                    f"Ausschnitt des Inhalts:\n{clean_text[:4000]}\n\n"
                    f"Antworte NUR mit validem JSON."
                )

                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.2,
                            "response_format": {"type": "json_object"},
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        parsed = json.loads(content)
                        return {
                            "summary": parsed.get("summary", f"Zusammenfassung für {file_name}"),
                            "keywords": parsed.get("keywords", []),
                            "document_type": parsed.get("document_type", "document"),
                            "entities": parsed.get("entities", {}),
                            "ai_model": self.model,
                        }
            except Exception as exc:
                logger.warning("LLM enrichment failed for %s: %s, falling back to heuristic", file_name, exc)

        # Heuristic NLP fallback
        return self._heuristic_enrich(clean_text, file_name)

    def _heuristic_enrich(self, text: str, file_name: str) -> Dict[str, Any]:
        """Extracts keywords, document types, and creates snippet summaries heuristically."""
        lower_text = text.lower()
        keywords = set()

        # Detect document type
        doc_type = "document"
        if any(kw in lower_text for kw in ["rechnung", "invoice", "rechnungsbetrag", "zahlungsziel", "ust-id"]):
            doc_type = "invoice"
            keywords.add("Rechnung")
        elif any(kw in lower_text for kw in ["vertrag", "contract", "vereinbarung", "unterschrift"]):
            doc_type = "contract"
            keywords.add("Vertrag")
        elif any(kw in lower_text for kw in ["angebot", "offer", "kostenvoranschlag"]):
            doc_type = "proposal"
            keywords.add("Angebot")
        elif any(kw in lower_text for kw in ["kontoauszug", "bank statement", "iban", "bic", "saldo"]):
            doc_type = "bank_statement"
            keywords.add("Kontoauszug")
        elif any(kw in lower_text for kw in ["grundriss", "schnitt", "cad", "autocad", "dwg", "maßstab"]):
            doc_type = "blueprint"
            keywords.add("Bauplan")

        # Extract dates (e.g. 2026, 2025, 01.05.2026)
        dates = re.findall(r"\b(202[0-9])\b", text)
        for d in set(dates):
            keywords.add(d)

        # Extract potential amounts (e.g. 145,50 € or 145.50 EUR)
        amounts = re.findall(r"\b\d{1,5}[,\.]\d{2}\s*(?:€|EUR|Euro)\b", text, re.IGNORECASE)

        # Clean snippet summary
        snippet = text[:350].strip()
        summary = f"{doc_type.capitalize()} '{file_name}': {snippet}..."

        return {
            "summary": summary,
            "keywords": sorted(list(keywords)),
            "document_type": doc_type,
            "entities": {"detected_amounts": amounts[:3], "detected_years": list(set(dates))},
            "ai_model": "heuristic_nlp",
        }
