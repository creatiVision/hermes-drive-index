"""
Unit tests for multi-modal parsers and composite extractor.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

import asyncio
from pathlib import Path

from hermes_auto_organizer.infrastructure.parsers.cad_parser import CadParser
from hermes_auto_organizer.infrastructure.parsers.composite import CompositeExtractor
from hermes_auto_organizer.infrastructure.parsers.doc_parser import DocumentParser
from hermes_auto_organizer.infrastructure.parsers.media_parser import MediaParser


def test_doc_parser_text_file(tmp_path: Path):
    doc_file = tmp_path / "spec.txt"
    doc_file.write_text("Specification for autonomous organizer.", encoding="utf-8")

    parser = DocumentParser()
    assert parser.supports(doc_file) is True

    extraction = asyncio.run(parser.extract_content(doc_file))
    assert extraction.extraction_strategy == "doc_plaintext"
    assert "Specification" in extraction.summary_text
    assert len(extraction.content_sha256) == 64


def test_cad_parser_dwg_fallback(tmp_path: Path):
    dwg_file = tmp_path / "drawing.dwg"
    dwg_file.write_bytes(b"AC1032" + b"\x00" * 20)

    parser = CadParser()
    assert parser.supports(dwg_file) is True

    extraction = asyncio.run(parser.extract_content(dwg_file))
    assert extraction.extraction_strategy == "cad_dwg_header"
    assert "AC1032" in extraction.summary_text
    assert extraction.metadata_json.get("header_version") == "AC1032"


def test_media_parser_support(tmp_path: Path):
    audio_file = tmp_path / "track.mp3"
    audio_file.write_bytes(b"ID3" + b"\x00" * 30)

    parser = MediaParser()
    assert parser.supports(audio_file) is True

    extraction = asyncio.run(parser.extract_content(audio_file))
    assert extraction.content_sha256 is not None


def test_composite_extractor_routing(tmp_path: Path):
    composite = CompositeExtractor()

    text_file = tmp_path / "notes.md"
    text_file.write_text("# Project Notes\nDiscussion details.", encoding="utf-8")

    extraction = asyncio.run(composite.extract_content(text_file))
    assert extraction.extraction_strategy == "doc_plaintext"
    assert "Project Notes" in extraction.summary_text

from unittest.mock import MagicMock, patch
import subprocess
from hermes_auto_organizer.infrastructure.parsers.image_parser import ImageParser


@patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract")
def test_image_parser_support(tmp_path: Path):
    parser = ImageParser()
    img_file = tmp_path / "invoice.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    with patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract"):
        assert parser.supports(img_file) is True

    txt_file = tmp_path / "doc.txt"
    txt_file.write_text("hello", encoding="utf-8")
    with patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract"):
        assert parser.supports(txt_file) is False


@patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract")
def test_image_parser_extract_content_ocr(tmp_path: Path):
    parser = ImageParser()
    img_file = tmp_path / "receipt.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 30)

    mock_proc = MagicMock()
    mock_proc.stdout = "Rechnung 2026-09-07 Netto 120,00 EUR"
    mock_proc.returncode = 0

    with patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract"), \
         patch("subprocess.run", return_value=mock_proc):
        extraction = asyncio.run(parser.extract_content(img_file))

    assert extraction.extraction_strategy == "ocr_tesseract"
    assert "Rechnung" in extraction.summary_text
    assert extraction.metadata_json["has_text"] is True
    assert extraction.metadata_json["ocr_engine"] == "tesseract"


@patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract")
def test_image_parser_timeout(tmp_path: Path):
    parser = ImageParser(timeout_seconds=5)
    img_file = tmp_path / "heavy.tiff"
    img_file.write_bytes(b"II*\x00" + b"\x00" * 30)

    with patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="tesseract", timeout=5)):
        extraction = asyncio.run(parser.extract_content(img_file))

    assert extraction.extraction_strategy == "ocr_timeout"
    assert "OCR timed out" in extraction.summary_text


def test_doc_parser_scanned_pdf_ocr_fallback(tmp_path: Path):
    parser = DocumentParser()
    pdf_file = tmp_path / "scanned_doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n" + b"\x00" * 50)

    # Mock pypdf reader returning 1 empty page
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_reader.pages = [mock_page]
    mock_reader.metadata = None

    # Mock _ocr_pdf to simulate OCR extraction
    mock_ocr_extraction = MagicMock()
    mock_ocr_extraction.extraction_strategy = "ocr_pdf_tesseract"
    mock_ocr_extraction.summary_text = "Scanned PDF scanned_doc.pdf (1 pages, OCR text): Inhaltsverzeichnis..."
    mock_ocr_extraction.metadata_json = {"ocr": True}
    mock_pypdf = MagicMock()
    mock_pypdf.PdfReader.return_value = mock_reader

    with patch("hermes_auto_organizer.infrastructure.parsers.doc_parser.pypdf", mock_pypdf), \
         patch.object(parser, "_ocr_pdf", return_value=mock_ocr_extraction):
        extraction = parser._extract_pdf(pdf_file, "mock_sha256")

    assert extraction.extraction_strategy == "ocr_pdf_tesseract"
    assert "OCR text" in extraction.summary_text


@patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract")
def test_composite_extractor_routes_image(tmp_path: Path):
    composite = CompositeExtractor()
    img_file = tmp_path / "diagram.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)

    mock_proc = MagicMock()
    mock_proc.stdout = "Architekturdiagramm Ebene 1"
    mock_proc.returncode = 0

    with patch("hermes_auto_organizer.infrastructure.parsers.image_parser._TESSERACT_BIN", "/usr/bin/tesseract"), \
         patch("subprocess.run", return_value=mock_proc):
        extraction = asyncio.run(composite.extract_content(img_file))

    assert extraction.extraction_strategy == "ocr_tesseract"
    assert "Architekturdiagramm" in extraction.summary_text
