"""FastAPI REST interface for AutoApply."""
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from loguru import logger
from agents.orchestrator import run_pipeline
from db.tracker import init_db, get_session, JobApplication

app = FastAPI(
    title="AutoApply API",
    description="AI-powered job application swarm for Naukri",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class ApplyRequest(BaseModel):
    dry_run: Optional[bool] = False
    min_score: Optional[int] = 70
    keywords: Optional[str] = None
    location: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "AutoApply"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume PDF or DOCX."""
    os.makedirs("data", exist_ok=True)
    dest = f"data/{file.filename}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": "Resume uploaded", "path": dest}


@app.post("/apply")
async def apply(request: ApplyRequest, background_tasks: BackgroundTasks):
    """Trigger the full AutoApply pipeline asynchronously."""
    background_tasks.add_task(
        run_pipeline,
        resume_path="data/resume.pdf",
        dry_run=request.dry_run,
    )
    return {"message": "AutoApply pipeline started in background", "dry_run": request.dry_run}


@app.get("/applications")
def list_applications(applied_only: bool = False, min_score: float = 0):
    """List all tracked job applications."""
    session = get_session()
    query = session.query(JobApplication).filter(JobApplication.score >= min_score)
    if applied_only:
        query = query.filter(JobApplication.applied == True)
    jobs = query.order_by(JobApplication.score.desc()).all()
    session.close()
    return [
        {
            "id": j.id,
            "job_title": j.job_title,
            "company": j.company,
            "location": j.location,
            "score": j.score,
            "applied": j.applied,
            "applied_at": j.applied_at,
            "status": j.status,
            "job_url": j.job_url,
        }
        for j in jobs
    ]


@app.get("/stats")
def get_stats():
    """Get summary statistics."""
    session = get_session()
    total = session.query(JobApplication).count()
    applied = session.query(JobApplication).filter(JobApplication.applied == True).count()
    avg_score = session.query(JobApplication).all()
    avg = sum(j.score or 0 for j in avg_score) / len(avg_score) if avg_score else 0
    session.close()
    return {"total_jobs": total, "applied": applied, "avg_score": round(avg, 1)}
