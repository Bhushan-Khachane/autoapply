"""Unit tests for ResumeParserAgent."""
import pytest
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from agents.resume_parser import extract_text_from_resume, parse_resume, _clean_json_response


def test_extract_text_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported resume format"):
        extract_text_from_resume("resume.txt")


def test_extract_text_unsupported_xlsx():
    with pytest.raises(ValueError, match="Unsupported resume format"):
        extract_text_from_resume("resume.xlsx")


@patch("agents.resume_parser.pdfplumber")
def test_extract_text_pdf(mock_pdfplumber):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "John Doe\nPython Developer\n5 years experience"
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

    result = extract_text_from_resume("resume.pdf")
    assert "John Doe" in result
    assert "Python Developer" in result


def test_clean_json_strips_markdown():
    raw = "```json\n{\"name\": \"John\"}\n```"
    result = _clean_json_response(raw)
    assert result == '{"name": "John"}'


@patch("agents.resume_parser.extract_text_from_resume")
@patch("agents.resume_parser.Agent")
@patch("os.path.exists", return_value=True)
def test_parse_resume_success(mock_exists, mock_agent_cls, mock_extract):
    mock_extract.return_value = "John Doe\nPython Developer\n5 years"
    valid_profile = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "9876543210",
        "location": "Nagpur",
        "total_experience_years": 5.0,
        "current_role": "Python Developer",
        "skills": ["Python", "FastAPI"],
        "education": [],
        "work_history": [],
        "certifications": [],
        "summary": "Experienced Python developer.",
    }
    mock_agent = MagicMock()
    mock_agent.start.return_value = json.dumps(valid_profile)
    mock_agent_cls.return_value = mock_agent

    result = parse_resume("data/resume.pdf")
    assert result["name"] == "John Doe"
    assert "Python" in result["skills"]


@patch("agents.resume_parser.extract_text_from_resume")
@patch("agents.resume_parser.Agent")
@patch("os.path.exists", return_value=True)
def test_parse_resume_fallback_on_bad_json(mock_exists, mock_agent_cls, mock_extract):
    mock_extract.return_value = "Some resume text"
    mock_agent = MagicMock()
    mock_agent.start.return_value = "This is not JSON"
    mock_agent_cls.return_value = mock_agent

    result = parse_resume("data/resume.pdf")
    assert "parse_error" in result
    assert result["score"] if "score" in result else True  # no crash


@patch("os.path.exists", return_value=False)
def test_parse_resume_file_not_found(mock_exists):
    with pytest.raises(FileNotFoundError):
        parse_resume("nonexistent.pdf")
