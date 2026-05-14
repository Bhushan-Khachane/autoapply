"""Unit tests for job scorer."""
import pytest
from unittest.mock import patch, MagicMock
from agents.job_scorer import score_job

SAMPLE_RESUME = {
    "name": "Rahul Sharma",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    "total_experience_years": 4,
    "current_role": "Backend Developer",
    "location": "Nagpur",
}

SAMPLE_JOB = {
    "job_id": "test_001",
    "job_title": "Python Backend Developer",
    "company": "TechCorp",
    "location": "Remote",
    "experience_required": "3-5 years",
    "salary": "10-15 LPA",
    "job_description": "We need a Python developer with FastAPI, PostgreSQL, and Docker experience.",
}


@patch("agents.job_scorer.Agent")
def test_score_job_returns_dict(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.start.return_value = '{"score": 85, "recommendation": "Strong match"}'
    mock_agent_cls.return_value = mock_agent

    result = score_job(SAMPLE_RESUME, SAMPLE_JOB)
    assert isinstance(result, dict)
    assert "score" in result
    assert 0 <= result["score"] <= 100


@patch("agents.job_scorer.Agent")
def test_score_job_handles_parse_error(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.start.return_value = "not valid json"
    mock_agent_cls.return_value = mock_agent

    result = score_job(SAMPLE_RESUME, SAMPLE_JOB)
    assert result["score"] == 0
