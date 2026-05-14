"""Orchestrator — coordinates the full AutoApply swarm pipeline."""
from loguru import logger
from datetime import datetime
from config.settings import settings
from db.tracker import init_db, get_session, upsert_job, get_unapplied_scored, job_already_applied
from agents.resume_parser import parse_resume
from agents.job_search import search_jobs
from agents.job_scorer import score_all_jobs
from agents.cover_letter import generate_cover_letter
from agents.applicator import apply_to_jobs
from agents.notifier import send_email_digest
import os


def run_pipeline(resume_path: str = None, dry_run: bool = False) -> dict:
    """
    Full AutoApply pipeline:
    1. Validate config
    2. Parse resume
    3. Search Naukri jobs
    4. Score jobs
    5. Save to DB
    6. Generate cover letters for eligible jobs
    7. Auto-apply (skip if dry_run)
    8. Send email digest
    Returns a summary dict.
    """
    resume_path = resume_path or settings.resume_path

    # Ensure output directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("db", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    logger.info("🚀 AutoApply pipeline started")

    # ── Step 0: Validate Config ─────────────────────────────────────────────
    if not dry_run:
        settings.validate_naukri_credentials()

    init_db()
    session = get_session()

    try:
        # ── Step 1: Parse Resume ──────────────────────────────────────────────
        logger.info("[1/7] Parsing resume...")
        resume_profile = parse_resume(resume_path, model=settings.model)
        logger.info(
            f"Resume parsed: name={resume_profile.get('name')} "
            f"skills={len(resume_profile.get('skills', []))} "
            f"experience={resume_profile.get('total_experience_years')}yr"
        )

        # ── Step 2: Search Jobs ───────────────────────────────────────────────
        logger.info("[2/7] Searching Naukri jobs...")
        all_jobs = search_jobs(
            keywords=settings.keyword_list,
            locations=settings.location_list,
            experience_min=settings.job_experience_min,
            experience_max=settings.job_experience_max,
            max_jobs=settings.max_jobs_per_run,
            headless=settings.headless,
        )
        logger.info(f"Found {len(all_jobs)} unique jobs")

        if not all_jobs:
            logger.warning("No jobs found. Check keywords/location in .env")
            return _empty_result()

        # ── Step 3: Score Jobs ────────────────────────────────────────────────
        logger.info("[3/7] Scoring jobs with LLM...")
        scored_jobs = score_all_jobs(resume_profile, all_jobs, model=settings.model)

        # ── Step 4: Save to DB ────────────────────────────────────────────────
        logger.info("[4/7] Saving to database...")
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

        # ── Step 5: Filter Eligible + Skip Already-Applied ───────────────────
        eligible_jobs = [
            j for j in scored_jobs
            if j["score"] >= settings.min_job_score
            and not job_already_applied(session, j["job_id"])
        ]
        logger.info(
            f"[5/7] {len(eligible_jobs)} eligible jobs (score >= {settings.min_job_score}, not yet applied)"
        )

        # ── Step 6: Generate Cover Letters ───────────────────────────────────
        logger.info(f"[6/7] Generating cover letters for {len(eligible_jobs)} jobs...")
        cover_letters: dict = {}
        for job in eligible_jobs:
            cl = generate_cover_letter(resume_profile, job, model=settings.model)
            cover_letters[job["job_id"]] = cl
            if cl:
                upsert_job(session, {"job_id": job["job_id"], "cover_letter": cl})

        # ── Step 7: Apply ─────────────────────────────────────────────────────
        applied_jobs: list = []
        failed_count = 0

        if dry_run:
            logger.info("[7/7] DRY RUN — skipping actual submissions")
            applied_jobs = list(eligible_jobs)
        elif eligible_jobs:
            logger.info(f"[7/7] Submitting applications for {len(eligible_jobs)} jobs...")
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
        else:
            logger.info("[7/7] No eligible jobs to apply to")

        # ── Step 8: Notify ────────────────────────────────────────────────────
        stats = {
            "total_found": len(all_jobs),
            "total_eligible": len(eligible_jobs),
            "total_applied": len(applied_jobs),
            "total_failed": failed_count,
            "min_score": settings.min_job_score,
        }
        send_email_digest(applied_jobs, stats)

        logger.info(
            f"✅ Pipeline complete | found={len(all_jobs)} eligible={len(eligible_jobs)} "
            f"applied={len(applied_jobs)} failed={failed_count}"
        )
        return {
            "resume_profile": resume_profile,
            "total_jobs_found": len(all_jobs),
            "scored_jobs": scored_jobs,
            "eligible_jobs": eligible_jobs,
            "applied_count": len(applied_jobs),
            "failed_count": failed_count,
            "stats": stats,
        }

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        raise
    finally:
        session.close()


def _empty_result() -> dict:
    return {
        "resume_profile": {},
        "total_jobs_found": 0,
        "scored_jobs": [],
        "eligible_jobs": [],
        "applied_count": 0,
        "failed_count": 0,
        "stats": {},
    }
