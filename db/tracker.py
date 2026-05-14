"""SQLite application tracker using SQLAlchemy."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config.settings import settings

Base = declarative_base()
engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)   # Naukri internal job ID
    job_title = Column(String)
    company = Column(String)
    location = Column(String)
    experience_required = Column(String)
    salary = Column(String)
    job_url = Column(String)
    job_description = Column(Text)
    score = Column(Float)
    applied = Column(Boolean, default=False)
    cover_letter = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="found")  # found | scored | applied | failed
    notes = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()


def upsert_job(session, job_data: dict) -> JobApplication:
    existing = session.query(JobApplication).filter_by(job_id=job_data["job_id"]).first()
    if existing:
        for k, v in job_data.items():
            setattr(existing, k, v)
        session.commit()
        return existing
    job = JobApplication(**job_data)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_unapplied_scored(session, min_score: float = 70.0):
    return (
        session.query(JobApplication)
        .filter(JobApplication.score >= min_score, JobApplication.applied == False)
        .all()
    )
