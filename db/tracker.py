"""SQLite application tracker using SQLAlchemy."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Optional
from config.settings import settings
import os

# Ensure the db directory exists
os.makedirs("db", exist_ok=True)

Base = declarative_base()
engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    job_title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, default="")
    experience_required = Column(String, default="")
    salary = Column(String, default="Not disclosed")
    job_url = Column(String, default="")
    job_description = Column(Text, default="")
    score = Column(Float, default=0.0)
    applied = Column(Boolean, default=False)
    cover_letter = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="found")  # found | scored | applied | failed
    notes = Column(Text, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def upsert_job(session: Session, job_data: dict) -> JobApplication:
    """
    Insert or selectively update a job record.
    Only updates fields that are explicitly provided (non-None) in job_data.
    """
    job_id = job_data.get("job_id")
    if not job_id:
        raise ValueError("job_data must contain a non-empty 'job_id'")

    existing = session.query(JobApplication).filter_by(job_id=job_id).first()
    if existing:
        # Only update keys that are present and non-None to avoid overwriting existing data
        for key, value in job_data.items():
            if key != "job_id" and value is not None:
                setattr(existing, key, value)
        try:
            session.commit()
            session.refresh(existing)
        except Exception:
            session.rollback()
            raise
        return existing

    # New record — build with provided data
    job = JobApplication(**{k: v for k, v in job_data.items() if v is not None})
    try:
        session.add(job)
        session.commit()
        session.refresh(job)
    except Exception:
        session.rollback()
        raise
    return job


def get_unapplied_scored(session: Session, min_score: float = 70.0):
    return (
        session.query(JobApplication)
        .filter(JobApplication.score >= min_score, JobApplication.applied == False)
        .order_by(JobApplication.score.desc())
        .all()
    )


def job_already_applied(session: Session, job_id: str) -> bool:
    """Quick check to skip already-applied jobs."""
    result = session.query(JobApplication.applied).filter_by(job_id=job_id).scalar()
    return bool(result)
