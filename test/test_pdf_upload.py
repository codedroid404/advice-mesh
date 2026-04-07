"""Unit tests for PDF reading functionality."""

import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest


def test_pymupdf_installed():
    """PyMuPDF should be importable."""
    import fitz
    assert hasattr(fitz, "open")


def test_read_pdf():
    """Should extract text from a simple PDF."""
    import fitz

    # Create a simple PDF in memory
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Senior Software Engineer\nRequirements: Python, C++")

    pdf_bytes = doc.tobytes()
    doc.close()

    # Read it back
    doc2 = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc2)
    doc2.close()

    assert "Senior Software Engineer" in text
    assert "Python" in text


def test_read_empty_pdf():
    """Empty PDF should return empty text."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    doc2 = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc2)
    doc2.close()

    assert text.strip() == ""
