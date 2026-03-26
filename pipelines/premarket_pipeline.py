import logging
from scheduler import update_last_run
from services.vol_regime_service import run_vol_pipeline

def run_premarket_pipeline():
    logging.info("Premarket pipeline starting...")
    try:
        run_vol_pipeline()
        update_last_run("premarket")
        logging.info("Premarket pipeline complete.")
    except Exception as e:
        logging.error(f"Premarket pipeline failed: {e}", exc_info=True)