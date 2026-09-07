"""
Document parser for PDF, DOCX, Markdown, and text files.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import subprocess
import tempfile

from hermes_auto_organizer.domain.models import FileExtraction
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256

logger = logging.getLogger("hermes_auto_organizer.parsers.doc")

_TESSERACT_BIN = shutil.which("tesseract")
_PDFTOPPM_BIN = shutil.which("pdftoppm")

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

try:
    import docx
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False


class DocumentParser:
    """Extracts text content and metadata from documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".csv", ".json"}

    @property
    def strategy_name(self) -> str:
        return "doc_text"

    def supports(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def extract_content(self, path: Path) -> FileExtraction:
        sha256 = compute_full_sha256(path)
        ext = path.suffix.lower()

        if ext == ".pdf" and _HAS_PYPDF:
            return self._extract_pdf(path, sha256)
        if ext == ".docx" and _HAS_DOCX:
            return self._extract_docx(path, sha256)
        return self._extract_plain_text(path, sha256)

    def _extract_pdf(self, path: Path, sha256: str) -> FileExtraction:
        try:
            reader = pypdf.PdfReader(str(path))
            total_pages = len(reader.pages)
            extracted_text = []

            # Sample first 5 pages and last 2 pages
            pages_to_sample = list(range(min(5, total_pages)))
            if total_pages > 5:
                pages_to_sample.extend(range(max(5, total_pages - 2), total_pages))

            for page_idx in pages_to_sample:
                text = reader.pages[page_idx].extract_text()
                if text:
                    extracted_text.append(text[:2000])

            joined_text = " ".join(extracted_text).strip()
            # If sufficient text was extracted, return pypdf result
            if len(joined_text) >= 40:
                summary = f"PDF {path.name} with {total_pages} pages. Snippet: {joined_text[:500]}..."
                metadata = {
                    "page_count": total_pages,
                    "author": reader.metadata.author if reader.metadata else None,
                    "title": reader.metadata.title if reader.metadata else None,
                }
                return FileExtraction(
                    content_sha256=sha256,
                    extraction_strategy="doc_pdf_pypdf",
                    summary_text=summary,
                    metadata_json=metadata,
                )

            # Scanned or image-only PDF: attempt OCR with pdftoppm + tesseract
            ocr_extraction = self._ocr_pdf(path, sha256, total_pages)
            if ocr_extraction is not None:
                return ocr_extraction

            summary = f"PDF {path.name} with {total_pages} pages (scanned/sparse text)."
            metadata = {
                "page_count": total_pages,
                "author": reader.metadata.author if reader.metadata else None,
                "title": reader.metadata.title if reader.metadata else None,
            }
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="doc_pdf_pypdf_sparse",
                summary_text=summary,
                metadata_json=metadata,
            )
        except Exception as e:
            logger.warning("Failed to extract PDF %s: %s", path, e)
            return self._fallback(path, sha256, f"PDF extraction error: {e}")

    def _ocr_pdf(self, path: Path, sha256: str, total_pages: int) -> FileExtraction | None:
        if not _PDFTOPPM_BIN or not _TESSERACT_BIN:
            return None
        try:
            with tempfile.TemporaryDirectory(prefix="ocr_pdf_") as tmpdir:
                tmp_prefix = Path(tmpdir) / "page"
                # Render first up to 3 pages
                max_pages = min(3, total_pages)
                cmd_render = [
                    _PDFTOPPM_BIN,
                    "-png",
                    "-r",
                    "150",
                    "-f",
                    "1",
                    "-l",
                    str(max_pages),
                    str(path),
                    str(tmp_prefix),
                ]
                subprocess.run(cmd_render, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45, check=True)

                rendered_images = sorted(Path(tmpdir).glob("page-*.png"))
                if not rendered_images:
                    return None

                ocr_fragments = []
                for img in rendered_images:
                    cmd_ocr = [_TESSERACT_BIN, str(img), "stdout", "-l", "deu+eng", "--psm", "3"]
                    proc = subprocess.run(cmd_ocr, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=30, check=False)
                    if proc.stdout.strip():
                        ocr_fragments.append(proc.stdout.strip())

                all_ocr = " ".join(" ".join(ocr_fragments).split())
                if not all_ocr:
                    return None

                summary = f"Scanned PDF {path.name} ({total_pages} pages, OCR text): {all_ocr[:500]}..."
                metadata = {
                    "page_count": total_pages,
                    "ocr": True,
                    "ocr_engine": "pdftoppm+tesseract",
                    "ocr_pages": len(rendered_images),
                    "ocr_chars": len(all_ocr),
                }
                return FileExtraction(
                    content_sha256=sha256,
                    extraction_strategy="ocr_pdf_tesseract",
                    summary_text=summary,
                    metadata_json=metadata,
                )
        except Exception as exc:
            logger.warning("OCR PDF extraction failed for %s: %s", path, exc)
            return None

    def _extract_docx(self, path: Path, sha256: str) -> FileExtraction:
        try:
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            joined_text = " ".join(paragraphs[:10])
            summary = f"DOCX document {path.name} with {len(paragraphs)} paragraphs. Snippet: {joined_text[:500]}..."
            metadata = {"paragraph_count": len(paragraphs)}
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="doc_docx",
                summary_text=summary,
                metadata_json=metadata,
            )
        except Exception as e:
            logger.warning("Failed to extract DOCX %s: %s", path, e)
            return self._fallback(path, sha256, f"DOCX extraction error: {e}")

    def _extract_plain_text(self, path: Path, sha256: str) -> FileExtraction:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(4000)
            summary = f"Text document {path.name}. Snippet: {content[:400]}..."
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="doc_plaintext",
                summary_text=summary,
                metadata_json={"encoding": "utf-8"},
            )
        except Exception as e:
            return self._fallback(path, sha256, f"Text read error: {e}")

    def _fallback(self, path: Path, sha256: str, reason: str) -> FileExtraction:
        return FileExtraction(
            content_sha256=sha256,
            extraction_strategy="doc_fallback",
            summary_text=f"Document {path.name} ({reason}).",
            metadata_json={"error": reason},
        )
