import logging
from datetime import date
from services.market_data import get_quotes_batch, get_quote
from services.fear_service import get_fear_gauges
from services.vol_regime_service import get_latest_regime
from scheduler import update_last_run
import db

SNAPSHOT_TICKERS = {
    "spx": "^GSPC", "qqq": "QQQ", "iwm": "IWM", "dia": "DIA",
    "vix": "^VIX", "hyg": "HYG", "tlt": "TLT", "uso": "USO", "gld": "GLD",
}

def run_close_pipeline():
    logging.info("Close pipeline starting...")
    try:
        today = date.today()
        quotes = get_quotes_batch(list(SNAPSHOT_TICKERS.values()))

        def price(key):
            return quotes.get(SNAPSHOT_TICKERS[key], {}).get("price", 0)

        def change_pct(key):
            return quotes.get(SNAPSHOT_TICKERS[key], {}).get("change_pct", 0)

        # Get regime from latest vol pipeline run
        regime = get_latest_regime()

        # Store daily snapshot
        db.insert("daily_snapshots",
            [(today, price("spx"), price("qqq"), price("iwm"), price("dia"),
              price("vix"), change_pct("vix"), regime.get("termStructure", {}).get("state", ""),
              0.0,  # put_call_ratio — requires separate data source
              price("hyg"), price("tlt"), price("uso"), price("gld"),
              regime.get("regime", ""), regime.get("regimeColor", ""),
              regime.get("assessment", ""))],
            ["date", "spx_close", "qqq_close", "iwm_close", "dia_close",
             "vix_close", "vix_change_pct", "term_structure", "put_call_ratio",
             "hyg_close", "tlt_close", "uso_close", "gld_close",
             "regime_label", "regime_color", "regime_assessment"])

        # Store fear snapshot at close
        gauges = get_fear_gauges()
        g = {item["name"]: item["value"] for item in gauges}
        vix_val = g.get("VIX", 0)
        db.insert("fear_snapshots",
            [(today, "close", vix_val, change_pct("vix"),
              regime.get("termStructure", {}).get("state", ""),
              g.get("MOVE", 0), g.get("HY OAS", 0),
              price("tlt"), price("uso"), price("gld"),
              g.get("Fear & Greed", 0), g.get("AAII Bull%", 0),
              g.get("NAAIM Exp.", 0),
              "Close snapshot")],
            ["date", "session", "vix", "vix_change", "term_structure_state",
             "move_index", "hy_oas_proxy", "tlt_price", "uso_price",
             "gld_price", "cnn_fear_greed", "aaii_bull_pct",
             "naaim_exposure", "regime_assessment"])

        update_last_run("close")
        logging.info("Close pipeline complete.")
    except Exception as e:
        logging.error(f"Close pipeline failed: {e}", exc_info=True)
