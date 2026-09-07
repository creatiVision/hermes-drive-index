"""
Image OCR parser using local Tesseract.

Supports .png, .jpg, .jpeg, .tiff, .tif, .webp, .bmp files.
Integrates with the content-hash cache pattern (SHA-256).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import subprocess

from hermes_auto_organizer.domain.models import FileExtraction
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256

logger = logging.getLogger("hermes_auto_organizer.parsers.image")

_TESSERACT_BIN = shutil.which("tesseract")


class ImageParser:
    """Extracts text content from images using local Tesseract OCR."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".bmp"}

    def __init__(self, languages: str = "deu+eng", timeout_seconds: int = 30) -> None:
        self.languages = languages
        self.timeout_seconds = timeout_seconds

    @property
    def strategy_name(self) -> str:
        return "ocr_tesseract"

    def supports(self, path: Path, mime_type: str | None = None) -> bool:
        if not _TESSERACT_BIN:
            return False
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def extract_content(self, path: Path) -> FileExtraction:
        sha256 = compute_full_sha256(path)
        if not _TESSERACT_BIN:
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="image_metadata",
                summary_text=f"Image {path.name} (Tesseract not found).",
                metadata_json={"file_name": path.name, "suffix": path.suffix},
            )

        try:
            # Run tesseract directly to stdout
            proc = subprocess.run(
                [
                    _TESSERACT_BIN,
                    str(path),
                    "stdout",
                    "-l",
                    self.languages,
                    "--psm",
                    "3",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            raw_text = proc.stdout.strip()
            clean_text = " ".join(raw_text.split())

            if clean_text:
                summary = f"Image {path.name} (OCR text): {clean_text[:500]}..."
                metadata = {
                    "ocr_engine": "tesseract",
                    "languages": self.languages,
                    "text_length": len(clean_text),
                    "has_text": True,
                }
            else:
                summary = f"Image {path.name} without discernible text."
                metadata = {
                    "ocr_engine": "tesseract",
                    "languages": self.languages,
                    "text_length": 0,
                    "has_text": False,
                }

            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="ocr_tesseract",
                summary_text=summary,
                metadata_json=metadata,
            )
        except subprocess.TimeoutExpired:
            logger.warning("OCR timed out after %ss for %s", self.timeout_seconds, path)
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="ocr_timeout",
                summary_text=f"Image {path.name} (OCR timed out).",
                metadata_json={"error": "timeout", "timeout_seconds": self.timeout_seconds},
            )
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", path, exc)
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="ocr_error",
                summary_text=f"Image {path.name} (OCR error: {exc}).",
                metadata_json={"error": str(exc)},
            )
