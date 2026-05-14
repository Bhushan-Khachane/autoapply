"""APScheduler — runs AutoApply daily at configured time with graceful shutdown."""
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from loguru import logger
from config.settings import settings
from agents.orchestrator import run_pipeline
import os

os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/scheduler_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
)


def scheduled_run() -> None:
    logger.info("⏰ Scheduled AutoApply run triggered")
    try:
        results = run_pipeline()
        logger.info(
            f"Scheduled run complete: applied={results.get('applied_count', 0)} "
            f"failed={results.get('failed_count', 0)}"
        )
    except Exception as e:
        logger.exception(f"Scheduled run failed: {e}")


def on_job_event(event):
    if event.exception:
        logger.error(f"Scheduler job crashed: {event.exception}")
    else:
        logger.info("Scheduler job completed successfully")


def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        scheduled_run,
        trigger=CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute),
        id="autoapply_daily",
        name="AutoApply Daily Job Search",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
        misfire_grace_time=3600,  # Allow up to 1hr late start
    )
    scheduler.add_listener(on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    def _shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping scheduler")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info(
        f"Scheduler started — running daily at "
        f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d} IST"
    )
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
