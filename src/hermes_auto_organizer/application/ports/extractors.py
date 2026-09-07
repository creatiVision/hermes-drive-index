"""
Content extractor port definition.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from hermes_auto_organizer.domain.models import FileExtraction


class ContentExtractorPort(Protocol):
    """Protocol for specialized multi-modal file parsers."""

    @property
    def strategy_name(self) -> str:
        """Name of the extraction strategy."""
        ...

    def supports(self, path: Path, mime_type: str | None = None) -> bool:
        """Return True if this extractor can process the file format."""
        ...

    async def extract_content(self, path: Path) -> FileExtraction:
        """Extract text summary and structured metadata from target file."""
        ...
