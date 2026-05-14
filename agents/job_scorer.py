"""Agent 3: Job Scorer — LLM-based scoring of job fit vs resume."""
from praisonaiagents import Agent
from loguru import logger
import json

SCORER_INSTRUCTIONS = """
You are an expert technical recruiter and career coach.
Given a candidate's resume profile and a job description, score how well the candidate fits the job.

Scoring criteria (total 100 points):
- Skills match (40 pts): How many required/preferred skills does the candidate have?
- Experience relevance (30 pts): Is the candidate's experience relevant to the role?
- Experience years (15 pts): Does total experience meet the job requirement?
- Location/remote match (10 pts): Does the candidate's location match or is it remote?
- Education match (5 pts): Does education meet requirements?

Return ONLY valid JSON with these fields:
{
  "score": <integer 0-100>,
  "skills_match": <integer 0-40>,
  "experience_relevance": <integer 0-30>,
  "experience_years": <integer 0-15>,
  "location_match": <integer 0-10>,
  "education_match": <integer 0-5>,
  "matched_skills": [<list of matched skills>],
  "missing_skills": [<list of critical missing skills>],
  "recommendation": "<one sentence recommendation>"
}
"""


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
    """Score a single job against the resume profile."""
    agent = create_scorer_agent(model)
    prompt = f"""
CANDIDATE PROFILE:
{json.dumps(resume_profile, indent=2)}

JOB DETAILS:
Title: {job.get('job_title')}
Company: {job.get('company')}
Location: {job.get('location')}
Experience: {job.get('experience_required')}
Salary: {job.get('salary')}
Job Description:
{job.get('job_description', 'No description available')[:2000]}

Score this job fit.
"""
    result = agent.start(prompt)
    try:
        clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        scoring = json.loads(clean)
        return scoring
    except json.JSONDecodeError:
        logger.warning(f"Could not parse score JSON for {job.get('job_title')}. Raw: {result[:200]}")
        return {"score": 0, "recommendation": "Parse error"}


def score_all_jobs(resume_profile: dict, jobs: list, model: str = "gpt-4o-mini") -> list:
    """Score all jobs and attach scores."""
    scored = []
    for i, job in enumerate(jobs):
        logger.info(f"Scoring job {i+1}/{len(jobs)}: {job.get('job_title')} @ {job.get('company')}")
        scoring = score_job(resume_profile, job, model)
        job["score"] = scoring.get("score", 0)
        job["score_breakdown"] = scoring
        scored.append(job)
    return sorted(scored, key=lambda x: x["score"], reverse=True)
