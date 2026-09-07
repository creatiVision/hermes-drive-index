"""
CAD parser for DXF and DWG technical drawings.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from hermes_auto_organizer.domain.models import FileExtraction
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256

logger = logging.getLogger("hermes_auto_organizer.parsers.cad")

try:
    import ezdxf
    _HAS_EZDXF = True
except ImportError:
    _HAS_EZDXF = False


class CadParser:
    """Extracts layers, block definitions, and text entities from CAD drawings."""

    SUPPORTED_EXTENSIONS = {".dxf", ".dwg"}

    @property
    def strategy_name(self) -> str:
        return "cad_ezdxf"

    def supports(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def extract_content(self, path: Path) -> FileExtraction:
        sha256 = compute_full_sha256(path)
        ext = path.suffix.lower()

        if ext == ".dxf" and _HAS_EZDXF:
            return self._extract_dxf(path, sha256)
        return self._extract_dwg_fallback(path, sha256)

    def _extract_dxf(self, path: Path, sha256: str) -> FileExtraction:
        try:
            doc = ezdxf.readfile(str(path))
            layers = [layer.dxf.name for layer in doc.layers]
            blocks = [block.name for block in doc.blocks if not block.name.startswith("*")]

            text_items = []
            msp = doc.modelspace()
            for entity in msp.query("TEXT MTEXT"):
                if entity.dxftype() == "TEXT":
                    text_items.append(entity.dxf.text)
                elif entity.dxftype() == "MTEXT":
                    text_items.append(entity.text)

            summary = (
                f"CAD drawing {path.name} contains {len(layers)} layers and {len(blocks)} blocks. "
                f"Sample text annotations: {', '.join(text_items[:5]) if text_items else 'none'}."
            )
            metadata = {
                "layers": layers[:50],
                "layer_count": len(layers),
                "blocks": blocks[:50],
                "block_count": len(blocks),
                "annotations_count": len(text_items),
                "acad_version": doc.acad_release,
            }
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="cad_ezdxf",
                summary_text=summary,
                metadata_json=metadata,
            )
        except Exception as e:
            logger.warning("Failed to parse DXF %s: %s", path, e)
            return self._extract_fallback(path, sha256, f"DXF parse error: {e}")

    def _extract_dwg_fallback(self, path: Path, sha256: str) -> FileExtraction:
        # DWG header inspection
        version_code = "UNKNOWN"
        try:
            with open(path, "rb") as f:
                header = f.read(6).decode("ascii", errors="ignore")
                if header.startswith("AC"):
                    version_code = header
        except Exception:
            pass

        summary = f"AutoCAD binary drawing {path.name} (Header version: {version_code})."
        metadata = {"cad_format": "DWG", "header_version": version_code}
        return FileExtraction(
            content_sha256=sha256,
            extraction_strategy="cad_dwg_header",
            summary_text=summary,
            metadata_json=metadata,
        )

    def _extract_fallback(self, path: Path, sha256: str, reason: str) -> FileExtraction:
        return FileExtraction(
            content_sha256=sha256,
            extraction_strategy="cad_fallback",
            summary_text=f"CAD file {path.name} (Metadata-only: {reason}).",
            metadata_json={"error": reason},
        )
