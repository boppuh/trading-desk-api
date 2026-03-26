from apscheduler.schedulers.background import BackgroundScheduler
import logging

scheduler = BackgroundScheduler(timezone="America/New_York")
last_run_times = {}


def start_scheduler():
    from pipelines.premarket_pipeline import run_premarket_pipeline

    # 7:55 AM ET weekdays
    scheduler.add_job(
        run_premarket_pipeline, "cron",
        hour=7, minute=55, day_of_week="mon-fri",
        id="premarket_pipeline", replace_existing=True,
    )
    scheduler.start()
    logging.info("APScheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logging.info("APScheduler stopped")


def update_last_run(pipeline_name: str):
    from datetime import datetime
    last_run_times[pipeline_name] = datetime.now().isoformat()
