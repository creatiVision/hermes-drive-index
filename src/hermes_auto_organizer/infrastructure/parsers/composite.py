"""
Composite multi-modal extractor routing to specialized parsers.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from hermes_auto_organizer.domain.models import FileExtraction
from hermes_auto_organizer.infrastructure.parsers.cad_parser import CadParser
from hermes_auto_organizer.infrastructure.parsers.doc_parser import DocumentParser
from hermes_auto_organizer.infrastructure.parsers.image_parser import ImageParser
from hermes_auto_organizer.infrastructure.parsers.media_parser import MediaParser
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256


class CompositeExtractor:
    """Dispatches files to the first supporting parser or falls back to basic metadata."""

    def __init__(self, parsers: Sequence[Any] | None = None) -> None:
        if parsers is None:
            self._parsers = [CadParser(), DocumentParser(), ImageParser(), MediaParser()]
        else:
            self._parsers = list(parsers)

    @property
    def strategy_name(self) -> str:
        return "composite_multimodal"

    def supports(self, path: Path, mime_type: str | None = None) -> bool:
        return True

    async def extract_content(self, path: Path) -> FileExtraction:
        for parser in self._parsers:
            if parser.supports(path):
                return await parser.extract_content(path)

        sha256 = compute_full_sha256(path)
        return FileExtraction(
            content_sha256=sha256,
            extraction_strategy="generic_stat",
            summary_text=f"Generic file {path.name} ({path.suffix}).",
            metadata_json={"file_name": path.name, "suffix": path.suffix},
        )
