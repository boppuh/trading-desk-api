import logging
from datetime import date
from scheduler import update_last_run
from services.vol_regime_service import run_vol_pipeline
from services.fear_service import get_premarket_fear
import db

def run_premarket_pipeline():
    logging.info("Premarket pipeline starting...")
    try:
        run_vol_pipeline()

        # Store fear snapshot at premarket (get_premarket_fear calls get_fear_gauges internally)
        fear = get_premarket_fear()
        vix_val = fear["vix"]["value"]
        move_val = fear["move"]["value"]
        fg_val = fear["fearGreed"]["value"]
        naaim_val = fear["naaim"]["value"]
        db.insert("fear_snapshots",
            [(date.today(), "premarket", vix_val, 0,
              "",  # term_structure_state filled by vol pipeline
              move_val, 0,
              0, 0, 0,  # tlt/uso/gld prices — not critical for premarket
              fg_val, 0,
              naaim_val,
              fear.get("assessment", ""))],
            ["date", "session", "vix", "vix_change", "term_structure_state",
             "move_index", "hy_oas_proxy", "tlt_price", "uso_price",
             "gld_price", "cnn_fear_greed", "aaii_bull_pct",
             "naaim_exposure", "regime_assessment"])

        update_last_run("premarket")
        logging.info("Premarket pipeline complete.")
    except Exception as e:
        logging.error(f"Premarket pipeline failed: {e}", exc_info=True)