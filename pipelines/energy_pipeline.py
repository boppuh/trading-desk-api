import logging
from datetime import datetime
from services.energy_service import get_commodity_strip, get_watchlist, score_exposure
from services.market_data import get_quotes_batch
from scheduler import update_last_run
import db

COMMODITY_SYMBOLS = ["BZ=F", "CL=F", "NG=F", "RB=F", "HO=F"]

def run_energy_pipeline():
    logging.info("Energy pipeline starting...")
    try:
        ts = datetime.now()
        quotes = get_quotes_batch(COMMODITY_SYMBOLS)
        rows = [(ts, sym, q["price"], q["change"], q["change_pct"], 0, 0, 0, 0)
                for sym, q in quotes.items()]
        db.insert("commodity_snapshots",
                  rows,
                  ["timestamp", "symbol", "price", "change", "pct_change", "open", "high", "low", "volume"])

        # Compute and store crack spread
        wti = quotes.get("CL=F", {}).get("price", 70)
        ho  = quotes.get("HO=F", {}).get("price", 0) * 42
        rb  = quotes.get("RB=F", {}).get("price", 0) * 42
        crack = (2 * rb + 1 * ho - 3 * wti) / 3
        db.insert("crack_spreads", [(ts, crack, ho - wti, ho - wti)],
                  ["timestamp", "spread_321", "jet_crack_approx", "diesel_crack"])

        # Store exposure rankings
        rankings = score_exposure()
        exp_rows = [(ts, r["ticker"], r["direction"], r["score"], r["thesis"], r["sector"])
                    for r in rankings]
        db.insert("exposure_rankings", exp_rows,
                  ["timestamp", "symbol", "direction", "score", "thesis", "sector"])

        update_last_run("energy")
        logging.info(f"Energy pipeline complete. WTI={wti:.2f} Crack={crack:.2f}")
    except Exception as e:
        logging.error(f"Energy pipeline failed: {e}", exc_info=True)
