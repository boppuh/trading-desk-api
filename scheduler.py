from apscheduler.schedulers.background import BackgroundScheduler
import logging

scheduler = BackgroundScheduler(timezone="America/New_York")
last_run_times = {}


def start_scheduler():
    from pipelines.premarket_pipeline import run_premarket_pipeline
    from pipelines.energy_pipeline import run_energy_pipeline
    from pipelines.close_pipeline import run_close_pipeline

    # 6:45 AM ET weekdays — energy commodity snapshot
    scheduler.add_job(
        run_energy_pipeline, "cron",
        hour=6, minute=45, day_of_week="mon-fri",
        id="energy_pipeline", replace_existing=True,
    )
    # 7:55 AM ET weekdays — premarket vol + fear
    scheduler.add_job(
        run_premarket_pipeline, "cron",
        hour=7, minute=55, day_of_week="mon-fri",
        id="premarket_pipeline", replace_existing=True,
    )
    # 3:15 PM ET weekdays — close-of-day snapshot
    scheduler.add_job(
        run_close_pipeline, "cron",
        hour=15, minute=15, day_of_week="mon-fri",
        id="close_pipeline", replace_existing=True,
    )
    scheduler.start()
    logging.info("APScheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logging.info("APScheduler stopped")


def update_last_run(pipeline_name: str):
    from datetime import datetime
    last_run_times[pipeline_name] = datetime.now().isoformat()
