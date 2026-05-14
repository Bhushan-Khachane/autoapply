"""Unit tests for resume parser."""
import pytest
from unittest.mock import patch, MagicMock
from agents.resume_parser import extract_text_from_resume
import tempfile
import os


def test_extract_text_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported resume format"):
        extract_text_from_resume("resume.txt")


@patch("agents.resume_parser.pdfplumber")
def test_extract_text_pdf(mock_pdfplumber):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "John Doe\nPython Developer\n5 years experience"
    mock_pdfplumber.open.return_value.__enter__.return_value.pages = [mock_page]

    result = extract_text_from_resume("resume.pdf")
    assert "John Doe" in result
    assert "Python Developer" in result
