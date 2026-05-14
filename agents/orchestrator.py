"""Orchestrator Agent — coordinates the full AutoApply swarm pipeline."""
from praisonaiagents import PraisonAIAgents, Agent, Task
from loguru import logger
from datetime import datetime
from config.settings import settings
from db.tracker import init_db, get_session, upsert_job, get_unapplied_scored
from agents.resume_parser import parse_resume
from agents.job_search import search_jobs
from agents.job_scorer import score_all_jobs
from agents.cover_letter import generate_cover_letter
from agents.applicator import apply_to_jobs
from agents.notifier import send_email_digest


def run_pipeline(resume_path: str = None, dry_run: bool = False):
    """
    Full AutoApply pipeline:
    1. Parse resume
    2. Search Naukri jobs
    3. Score jobs
    4. Save to DB
    5. Generate cover letters for top jobs
    6. Auto-apply to jobs with score >= min_score
    7. Send email digest
    """
    resume_path = resume_path or settings.resume_path
    logger.info("🚀 AutoApply pipeline started")
    init_db()
    session = get_session()

    # ── Step 1: Parse Resume ──────────────────────────────────
    logger.info("Step 1/6: Parsing resume...")
    resume_profile = parse_resume(resume_path, model=settings.model)
    logger.info(f"Resume parsed: {resume_profile.get('name')} | Skills: {len(resume_profile.get('skills', []))}")

    # ── Step 2: Search Jobs ───────────────────────────────────
    logger.info("Step 2/6: Searching Naukri jobs...")
    all_jobs = []
    for location in settings.location_list:
        jobs = search_jobs(
            keywords=settings.keyword_list,
            location=location,
            experience_min=settings.job_experience_min,
            experience_max=settings.job_experience_max,
            max_jobs=settings.max_jobs_per_run,
            headless=settings.headless,
        )
        all_jobs.extend(jobs)
    logger.info(f"Found {len(all_jobs)} jobs total")

    # ── Step 3: Score Jobs ────────────────────────────────────
    logger.info("Step 3/6: Scoring jobs with LLM...")
    scored_jobs = score_all_jobs(resume_profile, all_jobs, model=settings.model)

    # ── Step 4: Save to DB ────────────────────────────────────
    logger.info("Step 4/6: Saving jobs to database...")
    for job in scored_jobs:
        upsert_job(session, {
            "job_id": job["job_id"],
            "job_title": job["job_title"],
            "company": job["company"],
            "location": job["location"],
            "experience_required": job["experience_required"],
            "salary": job["salary"],
            "job_url": job["job_url"],
            "job_description": job.get("job_description", ""),
            "score": job["score"],
            "status": "scored",
        })

    # ── Step 5: Generate Cover Letters ───────────────────────
    eligible_jobs = [j for j in scored_jobs if j["score"] >= settings.min_job_score]
    logger.info(f"Step 5/6: Generating cover letters for {len(eligible_jobs)} eligible jobs (score >= {settings.min_job_score})...")
    cover_letters = {}
    for job in eligible_jobs:
        cl = generate_cover_letter(resume_profile, job, model=settings.model)
        cover_letters[job["job_id"]] = cl
        upsert_job(session, {"job_id": job["job_id"], "cover_letter": cl})

    # ── Step 6: Apply ─────────────────────────────────────────
    applied_jobs = []
    failed_count = 0
    if not dry_run and eligible_jobs:
        logger.info(f"Step 6/6: Applying to {len(eligible_jobs)} jobs...")
        results = apply_to_jobs(eligible_jobs, cover_letters, headless=settings.headless)
        for job in eligible_jobs:
            success = results.get(job["job_id"], False)
            upsert_job(session, {
                "job_id": job["job_id"],
                "applied": success,
                "applied_at": datetime.utcnow() if success else None,
                "status": "applied" if success else "failed",
            })
            if success:
                applied_jobs.append(job)
            else:
                failed_count += 1
    elif dry_run:
        logger.info("[DRY RUN] Skipping actual application submission")
        applied_jobs = eligible_jobs

    # ── Step 7: Notify ────────────────────────────────────────
    stats = {
        "total_found": len(all_jobs),
        "total_eligible": len(eligible_jobs),
        "total_applied": len(applied_jobs),
        "total_failed": failed_count,
    }
    send_email_digest(applied_jobs, stats)

    logger.info(f"✅ Pipeline complete. Applied to {len(applied_jobs)} jobs. Failed: {failed_count}")
    session.close()
    return {
        "resume_profile": resume_profile,
        "total_jobs_found": len(all_jobs),
        "eligible_jobs": eligible_jobs,
        "applied_count": len(applied_jobs),
        "failed_count": failed_count,
        "stats": stats,
    }
