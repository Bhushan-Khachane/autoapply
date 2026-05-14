"""Agent 1: Resume Parser — extracts structured data from PDF/DOCX resume."""
import pdfplumber
from docx import Document
from praisonaiagents import Agent
from loguru import logger
import json
import os

RESUME_PARSER_INSTRUCTIONS = """
You are an expert resume parser. Given raw resume text, extract the following fields as JSON:
- name (str)
- email (str)
- phone (str)
- location (str)
- total_experience_years (float)
- current_role (str)
- skills (list[str]): technical skills only
- education (list[dict]): [{degree, institution, year}]
- work_history (list[dict]): [{company, role, duration, key_achievements}]
- certifications (list[str])
- summary (str): 2-3 sentence professional summary

Return ONLY valid JSON, no markdown, no explanation.
"""


def extract_text_from_resume(resume_path: str) -> str:
    """Extract raw text from PDF or DOCX."""
    ext = os.path.splitext(resume_path)[1].lower()
    if ext == ".pdf":
        with pdfplumber.open(resume_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif ext in (".docx", ".doc"):
        doc = Document(resume_path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"Unsupported resume format: {ext}")


def create_resume_parser_agent(model: str = "gpt-4o-mini") -> Agent:
    return Agent(
        name="ResumeParserAgent",
        role="Resume Data Extractor",
        goal="Parse a resume and return structured JSON with all candidate details.",
        backstory="You are an HR tech specialist with 10 years of resume parsing experience.",
        instructions=RESUME_PARSER_INSTRUCTIONS,
        llm=model,
        verbose=False,
    )


def parse_resume(resume_path: str, model: str = "gpt-4o-mini") -> dict:
    """Full pipeline: extract text → run agent → return dict."""
    logger.info(f"Parsing resume: {resume_path}")
    raw_text = extract_text_from_resume(resume_path)
    agent = create_resume_parser_agent(model)
    result = agent.start(f"Parse this resume:\n\n{raw_text}")
    try:
        # Strip possible markdown code fences
        clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse resume JSON: {e}")
        return {"raw_text": raw_text, "parse_error": str(e)}
