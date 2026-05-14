"""Unit tests for JobScorerAgent."""
import pytest
from unittest.mock import patch, MagicMock
from agents.job_scorer import score_job, score_all_jobs, _clean_json_response

SAMPLE_RESUME = {
    "name": "Bhushan Khachane",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "SQLAlchemy"],
    "total_experience_years": 4,
    "current_role": "Backend Developer",
    "location": "Nagpur",
    "summary": "Experienced backend developer with Python and cloud expertise.",
}

SAMPLE_JOB = {
    "job_id": "test_001",
    "job_title": "Python Backend Developer",
    "company": "TechCorp India",
    "location": "Remote",
    "experience_required": "3-5 years",
    "salary": "10-15 LPA",
    "job_description": "We need a Python developer with FastAPI, PostgreSQL, and Docker experience.",
}


def test_clean_json_response_strips_fences():
    raw = "```json\n{\"score\": 85}\n```"
    assert _clean_json_response(raw) == '{"score": 85}'


def test_clean_json_response_no_fences():
    raw = '{"score": 85}'
    assert _clean_json_response(raw) == '{"score": 85}'


@patch("agents.job_scorer.Agent")
def test_score_job_valid_response(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.start.return_value = (
        '{"score": 85, "skills_match": 35, "experience_relevance": 25, '
        '"experience_years": 12, "location_match": 8, "education_match": 5, '
        '"matched_skills": ["Python", "FastAPI"], "missing_skills": [], '
        '"recommendation": "Strong match"}'
    )
    mock_agent_cls.return_value = mock_agent

    result = score_job(SAMPLE_RESUME, SAMPLE_JOB)
    assert isinstance(result, dict)
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert result["score"] == 85


@patch("agents.job_scorer.Agent")
def test_score_job_handles_invalid_json(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.start.return_value = "not valid json at all"
    mock_agent_cls.return_value = mock_agent

    result = score_job(SAMPLE_RESUME, SAMPLE_JOB)
    assert result["score"] == 0
    assert "Parse error" in result["recommendation"]


@patch("agents.job_scorer.Agent")
def test_score_job_handles_empty_response(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.start.return_value = ""
    mock_agent_cls.return_value = mock_agent

    result = score_job(SAMPLE_RESUME, SAMPLE_JOB)
    assert result["score"] == 0


@patch("agents.job_scorer.Agent")
def test_score_job_clamps_over_100(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.start.return_value = '{"score": 150, "recommendation": "Great"}'
    mock_agent_cls.return_value = mock_agent

    result = score_job(SAMPLE_RESUME, SAMPLE_JOB)
    assert result["score"] == 100  # clamped


@patch("agents.job_scorer.Agent")
def test_score_all_jobs_sorted_descending(mock_agent_cls):
    responses = ['{"score": 60}', '{"score": 90}', '{"score": 75}']
    call_count = 0

    def side_effect(prompt):
        nonlocal call_count
        resp = responses[call_count % len(responses)]
        call_count += 1
        return resp

    mock_agent = MagicMock()
    mock_agent.start.side_effect = side_effect
    mock_agent_cls.return_value = mock_agent

    jobs = [
        {**SAMPLE_JOB, "job_id": "j1"},
        {**SAMPLE_JOB, "job_id": "j2"},
        {**SAMPLE_JOB, "job_id": "j3"},
    ]
    scored = score_all_jobs(SAMPLE_RESUME, jobs)
    scores = [j["score"] for j in scored]
    assert scores == sorted(scores, reverse=True)
