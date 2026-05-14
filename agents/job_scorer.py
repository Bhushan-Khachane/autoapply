"""Agent 3: Job Scorer — LLM-based scoring of job fit vs resume."""
from praisonaiagents import Agent
from loguru import logger
from typing import List, Dict
import json
import re


SCORER_INSTRUCTIONS = """
You are an expert technical recruiter and career coach.
Given a candidate's resume profile and a job description, score how well the candidate fits the job.

Scoring criteria (total 100 points):
- Skills match (40 pts): How many required/preferred skills does the candidate have?
- Experience relevance (30 pts): Is the candidate's experience relevant to the role?
- Experience years (15 pts): Does total experience meet the job requirement?
- Location/remote match (10 pts): Does candidate location match or is it remote?
- Education match (5 pts): Does education meet requirements?

Return ONLY valid JSON (no markdown, no explanation):
{
  "score": <integer 0-100>,
  "skills_match": <integer 0-40>,
  "experience_relevance": <integer 0-30>,
  "experience_years": <integer 0-15>,
  "location_match": <integer 0-10>,
  "education_match": <integer 0-5>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3"],
  "recommendation": "<one sentence recommendation>"
}
"""


def _clean_json_response(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip())
    return cleaned.strip()


def create_scorer_agent(model: str = "gpt-4o-mini") -> Agent:
    return Agent(
        name="JobScorerAgent",
        role="Technical Recruiter & Career Coach",
        goal="Score how well a candidate's resume matches a job description on a scale of 0-100.",
        backstory="You have 15 years of experience as a technical recruiter at top tech companies in India.",
        instructions=SCORER_INSTRUCTIONS,
        llm=model,
        verbose=False,
    )


def score_job(resume_profile: dict, job: dict, model: str = "gpt-4o-mini") -> dict:
    """Score a single job against the resume profile. Always returns a valid dict."""
    agent = create_scorer_agent(model)
    prompt = (
        f"CANDIDATE PROFILE:\n{json.dumps(resume_profile, indent=2)}\n\n"
        f"JOB DETAILS:\n"
        f"Title: {job.get('job_title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Experience: {job.get('experience_required', '')}\n"
        f"Salary: {job.get('salary', '')}\n"
        f"Description:\n{job.get('job_description', 'No description available')[:2000]}\n\n"
        f"Score this job fit. Return JSON only."
    )
    result = agent.start(prompt)

    if not result:
        logger.warning(f"Empty score response for: {job.get('job_title')}")
        return {"score": 0, "matched_skills": [], "missing_skills": [], "recommendation": "No response"}

    try:
        parsed = json.loads(_clean_json_response(result))
        # Clamp score to 0-100
        parsed["score"] = max(0, min(100, int(parsed.get("score", 0))))
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Score parse error for '{job.get('job_title')}': {e}. Raw: {result[:200]}")
        return {
            "score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "recommendation": f"Parse error: {str(e)}",
        }


def score_all_jobs(resume_profile: dict, jobs: List[Dict], model: str = "gpt-4o-mini") -> List[Dict]:
    """Score all jobs, attach scores, return sorted descending by score."""
    scored: List[Dict] = []
    for i, job in enumerate(jobs):
        logger.info(f"Scoring [{i+1}/{len(jobs)}]: {job.get('job_title')} @ {job.get('company')}")
        scoring = score_job(resume_profile, job, model)
        # Work on a copy to avoid mutating the original list
        job_copy = dict(job)
        job_copy["score"] = scoring.get("score", 0)
        job_copy["score_breakdown"] = scoring
        scored.append(job_copy)
    return sorted(scored, key=lambda x: x["score"], reverse=True)
