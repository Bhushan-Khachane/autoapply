"""Agent 4: Cover Letter Generator — personalised cover letters per job."""
from praisonaiagents import Agent
from loguru import logger
import json


COVER_LETTER_INSTRUCTIONS = """
You are an expert career coach who writes compelling, personalized cover letters.
Given a candidate profile and job details, write a professional cover letter that:
1. Opens with a strong, attention-grabbing paragraph mentioning the specific role and company
2. Highlights 2-3 most relevant experiences/skills that match the job
3. Shows genuine enthusiasm for the company/role with specific reasons
4. Closes with a clear call to action

Keep it concise (250-350 words). Do not use generic phrases like 'I am writing to apply for...'.
Write in first person. Sound human, confident, and specific.
Return ONLY the cover letter text. No subject line, no headers, no markdown.
"""


def create_cover_letter_agent(model: str = "gpt-4o-mini") -> Agent:
    return Agent(
        name="CoverLetterAgent",
        role="Professional Cover Letter Writer",
        goal="Write a compelling, tailored cover letter that gets interviews.",
        backstory="You are a career coach who has helped 500+ professionals land jobs at top companies.",
        instructions=COVER_LETTER_INSTRUCTIONS,
        llm=model,
        verbose=False,
    )


def generate_cover_letter(resume_profile: dict, job: dict, model: str = "gpt-4o-mini") -> str:
    """Generate a tailored cover letter. Returns empty string on failure."""
    agent = create_cover_letter_agent(model)
    prompt = (
        f"CANDIDATE PROFILE:\n{json.dumps(resume_profile, indent=2)}\n\n"
        f"TARGET JOB:\n"
        f"Title: {job.get('job_title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Description: {job.get('job_description', '')[:1500]}\n\n"
        f"Write a tailored cover letter for this candidate applying to this job."
    )
    try:
        cover_letter = agent.start(prompt)
        if cover_letter:
            logger.info(f"Cover letter generated: {job.get('job_title')} @ {job.get('company')}")
            return cover_letter.strip()
        logger.warning(f"Empty cover letter response for: {job.get('job_title')}")
        return ""
    except Exception as e:
        logger.error(f"Cover letter generation failed for {job.get('job_title')}: {e}")
        return ""
