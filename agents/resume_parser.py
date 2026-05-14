"""Agent 1: Resume Parser — extracts structured data from PDF/DOCX resume."""
import pdfplumber
from docx import Document
from praisonaiagents import Agent
from loguru import logger
import json
import os
import re


RESUME_PARSER_INSTRUCTIONS = """
You are an expert resume parser. Given raw resume text, extract the following fields as JSON:
- name (str)
- email (str)
- phone (str)
- location (str)
- total_experience_years (float)
- current_role (str)
- skills (list[str]): technical skills only
- education (list[dict]): [{"degree": "", "institution": "", "year": ""}]
- work_history (list[dict]): [{"company": "", "role": "", "duration": "", "key_achievements": []}]
- certifications (list[str])
- summary (str): 2-3 sentence professional summary

Return ONLY valid JSON. No markdown fences, no explanation, no extra text.
"""


def extract_text_from_resume(resume_path: str) -> str:
    """Extract raw text from PDF or DOCX. Raises ValueError for unsupported formats."""
    ext = os.path.splitext(resume_path)[1].lower()
    if ext == ".pdf":
        with pdfplumber.open(resume_path) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages_text)
    elif ext in (".docx", ".doc"):
        doc = Document(resume_path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"Unsupported resume format: {ext}. Use PDF or DOCX.")


def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences and whitespace from LLM JSON responses."""
    # Remove ```json ... ``` or ``` ... ``` fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip())
    return cleaned.strip()


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
    """Full pipeline: extract text -> run agent -> return dict."""
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume not found at: {resume_path}")

    logger.info(f"Parsing resume: {resume_path}")
    raw_text = extract_text_from_resume(resume_path)

    if not raw_text.strip():
        raise ValueError(f"Could not extract text from resume: {resume_path}")

    agent = create_resume_parser_agent(model)
    result = agent.start(f"Parse this resume and return JSON only:\n\n{raw_text}")

    if not result:
        raise RuntimeError("ResumeParserAgent returned empty response")

    try:
        clean = _clean_json_response(result)
        parsed = json.loads(clean)
        # Ensure required keys exist with defaults
        parsed.setdefault("skills", [])
        parsed.setdefault("work_history", [])
        parsed.setdefault("education", [])
        parsed.setdefault("certifications", [])
        parsed.setdefault("total_experience_years", 0)
        parsed.setdefault("summary", "")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse resume JSON: {e}. Raw response: {result[:300]}")
        # Fallback: return minimal profile with raw text
        return {
            "name": "Unknown",
            "email": "",
            "phone": "",
            "location": "",
            "total_experience_years": 0,
            "current_role": "",
            "skills": [],
            "education": [],
            "work_history": [],
            "certifications": [],
            "summary": raw_text[:500],
            "raw_text": raw_text,
            "parse_error": str(e),
        }
