"""Unit tests for PDF text extraction function extract_pdf."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from pypdf import PdfWriter

from hermes_drive_index.core.extract import extract_pdf


def test_extract_pdf_empty_pdf(tmp_path: Path):
    pdf_path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.write(pdf_path)

    text = extract_pdf(pdf_path)
    assert text == ""


def test_extract_pdf_mocked_pages(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock content")

    mock_page1 = mock.MagicMock()
    mock_page1.extract_text.return_value = "Page 1 Content"

    mock_page2 = mock.MagicMock()
    mock_page2.extract_text.return_value = None  # test None return

    mock_page3 = mock.MagicMock()
    mock_page3.extract_text.return_value = "   "  # whitespace only

    mock_page4 = mock.MagicMock()
    mock_page4.extract_text.return_value = "Page 4 Content"

    mock_reader = mock.MagicMock()
    mock_reader.pages = [mock_page1, mock_page2, mock_page3, mock_page4]

    with mock.patch("pypdf.PdfReader", return_value=mock_reader):
        result = extract_pdf(pdf_path)

    assert result == "Page 1 Content\n\nPage 4 Content"


def test_extract_pdf_page_exception_handling(tmp_path: Path):
    pdf_path = tmp_path / "corrupt_page.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock content")

    mock_page1 = mock.MagicMock()
    mock_page1.extract_text.return_value = "Page 1 ok"

    mock_page2 = mock.MagicMock()
    mock_page2.extract_text.side_effect = RuntimeError("Bad font encoding")

    mock_page3 = mock.MagicMock()
    mock_page3.extract_text.return_value = "Page 3 ok"

    mock_reader = mock.MagicMock()
    mock_reader.pages = [mock_page1, mock_page2, mock_page3]

    with mock.patch("pypdf.PdfReader", return_value=mock_reader):
        result = extract_pdf(pdf_path)

    expected = "Page 1 ok\n\n\n[page 2 extraction error: Bad font encoding]\n\n\nPage 3 ok"
    assert result == expected
