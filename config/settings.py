"""Centralised configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    model: str = "gpt-4o-mini"

    # Naukri credentials — required; will raise clear error if missing
    naukri_email: str = ""
    naukri_password: str = ""

    # Job Search
    job_keywords: str = "Python Developer"
    job_location: str = "Remote"
    job_experience_min: int = 0
    job_experience_max: int = 10
    job_salary_min: int = 0
    max_jobs_per_run: int = 50
    min_job_score: int = 70

    # Email notifications (optional)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notify_email: str = ""

    # App
    resume_path: str = "data/resume.pdf"
    db_url: str = "sqlite:///db/autoapply.db"
    log_level: str = "INFO"
    headless: bool = True
    schedule_hour: int = 9
    schedule_minute: int = 0

    @property
    def keyword_list(self) -> List[str]:
        return [k.strip() for k in self.job_keywords.split(",") if k.strip()]

    @property
    def location_list(self) -> List[str]:
        return [loc.strip() for loc in self.job_location.split(",") if loc.strip()]

    def validate_naukri_credentials(self) -> None:
        """Call this before running the pipeline to give a clear error message."""
        if not self.naukri_email or not self.naukri_password:
            raise ValueError(
                "NAUKRI_EMAIL and NAUKRI_PASSWORD must be set in your .env file before running AutoApply."
            )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
