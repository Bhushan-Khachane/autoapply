"""AutoApply — Entry point."""
import argparse
from loguru import logger
from agents.orchestrator import run_pipeline
from config.settings import settings
import sys

logger.remove()
logger.add(sys.stderr, level=settings.log_level)
logger.add("logs/autoapply_{time}.log", rotation="1 day", retention="7 days", level="DEBUG")


def main():
    parser = argparse.ArgumentParser(description="AutoApply — AI Job Application Swarm")
    parser.add_argument("--resume", type=str, default=settings.resume_path, help="Path to resume PDF/DOCX")
    parser.add_argument("--dry-run", action="store_true", help="Score jobs but don't actually apply")
    parser.add_argument("--min-score", type=int, default=settings.min_job_score, help="Minimum score to apply (0-100)")
    args = parser.parse_args()

    logger.info(f"Starting AutoApply | Resume: {args.resume} | Min Score: {args.min_score} | Dry Run: {args.dry_run}")

    results = run_pipeline(resume_path=args.resume, dry_run=args.dry_run)

    print("\n" + "="*60)
    print("📊 AutoApply Summary")
    print("="*60)
    print(f"👤 Candidate: {results['resume_profile'].get('name', 'Unknown')}")
    print(f"🔍 Jobs Found: {results['total_jobs_found']}")
    print(f"⭐ Eligible (score >= {args.min_score}): {len(results['eligible_jobs'])}")
    print(f"✅ Applied: {results['applied_count']}")
    print(f"❌ Failed: {results['failed_count']}")
    print("="*60)

    if results['eligible_jobs']:
        print("\n🏆 Top Scored Jobs:")
        for job in results['eligible_jobs'][:10]:
            print(f"  [{job['score']:3.0f}] {job['job_title']} @ {job['company']} — {job['location']}")


if __name__ == "__main__":
    main()
