"""APScheduler — runs AutoApply daily at configured time."""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from config.settings import settings
from agents.orchestrator import run_pipeline


def scheduled_run():
    logger.info("⏰ Scheduled AutoApply run triggered")
    run_pipeline()


def start_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(
        scheduled_run,
        trigger=CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute),
        id="autoapply_daily",
        name="AutoApply Daily Job Search",
        replace_existing=True,
    )
    logger.info(f"Scheduler started — running daily at {settings.schedule_hour:02d}:{settings.schedule_minute:02d}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    start_scheduler()
