"""AutoApply — CLI entry point."""
import argparse
import sys
import os
from loguru import logger
from config.settings import settings

# Ensure output dirs exist before logger tries to write
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("db", exist_ok=True)

logger.remove()
logger.add(sys.stderr, level=settings.log_level, colorize=True)
logger.add(
    "logs/autoapply_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AutoApply — AI Job Application Swarm for Naukri",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--resume", type=str, default=settings.resume_path,
        help="Path to resume PDF or DOCX"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Score and rank jobs but do NOT submit any applications"
    )
    parser.add_argument(
        "--min-score", type=int, default=settings.min_job_score,
        help="Minimum score (0-100) required to auto-apply"
    )
    args = parser.parse_args()

    if not os.path.exists(args.resume):
        logger.error(f"Resume not found: {args.resume}")
        logger.error("Place your resume PDF at data/resume.pdf or pass --resume <path>")
        sys.exit(1)

    logger.info(
        f"Starting AutoApply | resume={args.resume} | "
        f"min_score={args.min_score} | dry_run={args.dry_run}"
    )

    # Late import to ensure logger is set up first
    from agents.orchestrator import run_pipeline

    try:
        results = run_pipeline(resume_path=args.resume, dry_run=args.dry_run)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        sys.exit(1)

    sep = "=" * 60
    print(f"\n{sep}")
    print("📊 AutoApply Summary")
    print(sep)
    print(f"👤 Candidate : {results['resume_profile'].get('name', 'Unknown')}")
    print(f"🔍 Jobs Found : {results['total_jobs_found']}")
    print(f"⭐ Eligible   : {len(results['eligible_jobs'])} (score >= {args.min_score})")
    print(f"✅ Applied    : {results['applied_count']}")
    print(f"❌ Failed     : {results['failed_count']}")
    print(sep)

    if results["eligible_jobs"]:
        print("\n🏆 Top Matched Jobs:")
        for job in results["eligible_jobs"][:10]:
            print(
                f"  [{job['score']:3.0f}] {job['job_title']:<40} "
                f"@ {job['company']:<25} — {job['location']}"
            )


if __name__ == "__main__":
    main()
