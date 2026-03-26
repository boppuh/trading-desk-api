import logging
from datetime import date
from scheduler import update_last_run
from services.vol_regime_service import run_vol_pipeline
from services.fear_service import get_fear_gauges, get_premarket_fear
from services.market_data import get_quote
import db

def run_premarket_pipeline():
    logging.info("Premarket pipeline starting...")
    try:
        run_vol_pipeline()

        # Store fear snapshot at premarket
        fear = get_premarket_fear()
        gauges = get_fear_gauges()
        g = {item["name"]: item["value"] for item in gauges}
        vix_q = get_quote("^VIX")
        db.insert("fear_snapshots",
            [(date.today(), "premarket", g.get("VIX", 0), vix_q.get("change_pct", 0),
              "",  # term_structure_state filled by vol pipeline
              g.get("MOVE", 0), g.get("HY OAS", 0),
              0, 0, 0,  # tlt/uso/gld prices — not critical for premarket
              g.get("Fear & Greed", 0), g.get("AAII Bull%", 0),
              g.get("NAAIM Exp.", 0),
              fear.get("assessment", ""))],
            ["date", "session", "vix", "vix_change", "term_structure_state",
             "move_index", "hy_oas_proxy", "tlt_price", "uso_price",
             "gld_price", "cnn_fear_greed", "aaii_bull_pct",
             "naaim_exposure", "regime_assessment"])

        update_last_run("premarket")
        logging.info("Premarket pipeline complete.")
    except Exception as e:
        logging.error(f"Premarket pipeline failed: {e}", exc_info=True)