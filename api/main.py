"""FastAPI REST interface for AutoApply."""
import os
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import shutil
from loguru import logger
from agents.orchestrator import run_pipeline
from db.tracker import init_db, get_session, JobApplication
import concurrent.futures


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create directories and initialise DB."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("db", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    init_db()
    logger.info("AutoApply API started")
    yield
    logger.info("AutoApply API shutting down")


app = FastAPI(
    title="AutoApply API",
    description="AI-powered job application swarm for Naukri",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApplyRequest(BaseModel):
    dry_run: Optional[bool] = False
    min_score: Optional[int] = 70
    resume_path: Optional[str] = None


def _run_pipeline_in_thread(resume_path: str, dry_run: bool):
    """
    Run the pipeline in a separate thread to avoid asyncio event loop conflicts.
    run_pipeline uses asyncio.run() internally (via Playwright), which cannot be called
    from within FastAPI's async event loop. Using ThreadPoolExecutor solves this.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_pipeline, resume_path, dry_run)
        return future.result(timeout=900)


@app.get("/health")
def health():
    return {"status": "ok", "service": "AutoApply", "version": "1.0.0"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume PDF or DOCX."""
    allowed_extensions = {".pdf", ".docx", ".doc"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'. Use PDF or DOCX.")

    os.makedirs("data", exist_ok=True)
    dest = f"data/resume{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info(f"Resume uploaded: {dest}")
    return {"message": "Resume uploaded successfully", "path": dest, "filename": file.filename}


@app.post("/apply")
async def apply(request: ApplyRequest, background_tasks: BackgroundTasks):
    """Trigger the full AutoApply pipeline in a background thread."""
    resume_path = request.resume_path or "data/resume.pdf"
    if not os.path.exists(resume_path):
        raise HTTPException(
            status_code=400,
            detail=f"Resume not found at '{resume_path}'. Upload it first via POST /upload-resume"
        )
    background_tasks.add_task(_run_pipeline_in_thread, resume_path, request.dry_run)
    return {
        "message": "AutoApply pipeline started in background",
        "dry_run": request.dry_run,
        "resume_path": resume_path,
    }


@app.get("/applications")
def list_applications(
    applied_only: bool = False,
    min_score: float = 0,
    limit: int = 100,
    offset: int = 0,
):
    """List all tracked job applications with optional filters."""
    session = get_session()
    try:
        query = session.query(JobApplication).filter(JobApplication.score >= min_score)
        if applied_only:
            query = query.filter(JobApplication.applied == True)
        jobs = query.order_by(JobApplication.score.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": j.id,
                "job_id": j.job_id,
                "job_title": j.job_title,
                "company": j.company,
                "location": j.location,
                "salary": j.salary,
                "score": j.score,
                "applied": j.applied,
                "applied_at": j.applied_at.isoformat() if j.applied_at else None,
                "status": j.status,
                "job_url": j.job_url,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
    finally:
        session.close()


@app.get("/applications/{job_id}")
def get_application(job_id: str):
    """Get details of a specific application including cover letter."""
    session = get_session()
    try:
        job = session.query(JobApplication).filter_by(job_id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Application not found")
        return {
            "job_id": job.job_id,
            "job_title": job.job_title,
            "company": job.company,
            "location": job.location,
            "salary": job.salary,
            "score": job.score,
            "applied": job.applied,
            "applied_at": job.applied_at.isoformat() if job.applied_at else None,
            "status": job.status,
            "job_url": job.job_url,
            "job_description": job.job_description,
            "cover_letter": job.cover_letter,
        }
    finally:
        session.close()


@app.get("/stats")
def get_stats():
    """Get summary statistics."""
    session = get_session()
    try:
        all_jobs = session.query(JobApplication).all()
        total = len(all_jobs)
        applied = sum(1 for j in all_jobs if j.applied)
        scores = [j.score for j in all_jobs if j.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        by_status = {}
        for j in all_jobs:
            by_status[j.status] = by_status.get(j.status, 0) + 1
        return {
            "total_jobs_tracked": total,
            "applied": applied,
            "avg_score": avg_score,
            "by_status": by_status,
        }
    finally:
        session.close()
