import numpy as np
import logging
from datetime import date
from services.market_data import get_quote, get_history
from config import settings, VOL_INSTRUMENTS, FORWARD_RETURNS
import db

def run_vol_pipeline():
    """Full vol regime pipeline. Called by premarket_pipeline.py at 7:55 AM ET."""
    quotes = {t: get_quote(t) for t in VOL_INSTRUMENTS}

    vix = quotes["^VIX"]["price"]
    vix_prev = vix - quotes["^VIX"]["change"]
    vix_change = quotes["^VIX"]["change"]
    vix_change_pct = quotes["^VIX"]["change_pct"]

    # 20-day realized vol from ClickHouse ohlcv_5m or yfinance
    spx_hist = _get_spx_closes_25()
    log_returns = np.log(np.array(spx_hist[1:]) / np.array(spx_hist[:-1]))
    realized_vol_20d = float(np.std(log_returns[-20:]) * np.sqrt(252) * 100)

    # Implied-Realized spread
    impl_real_spread = vix - realized_vol_20d

    # Term structure
    vixy = quotes["VIXY"]["price"]
    ts_spread_pct = (vixy - vix) / vix * 100
    if ts_spread_pct > 2:
        term_structure = "contango"
    elif ts_spread_pct < -2:
        term_structure = "backwardation"
    else:
        term_structure = "flat"

    # Regime classification
    if vix < 15:
        regime, sub_regime = "complacent", ""
    elif vix <= 25:
        regime, sub_regime = "hedged_orderly", "normal"
    elif vix <= 30:
        regime, sub_regime = "hedged_orderly", "fear"
    else:
        regime, sub_regime = "panic", ""

    # Composite score (0=complacent, 100=panic)
    oil = quotes["CL=F"]
    move = quotes["^MOVE"]["price"]
    move_prev = move - quotes["^MOVE"]["change"]

    vix_score   = min(vix / 50 * 100, 100)
    ts_score    = 100 if term_structure == "backwardation" else 50 if term_structure == "flat" else 0
    ir_score    = max(0, min((-impl_real_spread + 10) / 20 * 100, 100))
    move_score  = min(move / 200 * 100, 100)
    oil_score   = min(abs(oil["change_pct"]) / 5 * 100, 100)
    composite   = vix_score*0.30 + ts_score*0.20 + ir_score*0.20 + move_score*0.15 + oil_score*0.15

    spx = quotes["^GSPC"]
    row = (
        date.today(), vix, vix_change, vix_change_pct,
        spx["price"], spx["change_pct"],
        oil["price"], oil["change_pct"],
        move, quotes["^MOVE"]["change_pct"],
        vixy, realized_vol_20d, impl_real_spread,
        term_structure, ts_spread_pct,
        regime, sub_regime, composite,
    )
    cols = [
        "date", "vix_spot", "vix_change", "vix_change_pct",
        "spx_close", "spx_change_pct", "oil_wti", "oil_change_pct",
        "move_index", "move_change_pct", "vixy_close",
        "realized_vol_20d", "implied_realized_spread",
        "term_structure_state", "term_structure_spread_pct",
        "regime", "sub_regime", "composite_score",
    ]
    db.insert("vol_regime_daily", [row], cols)
    logging.info(f"Vol pipeline complete: {regime} | VIX {vix:.2f} | score {composite:.1f}")
    return get_latest_regime()

def get_latest_regime() -> dict:
    rows = db.execute(
        "SELECT * FROM vol_regime_daily FINAL ORDER BY date DESC LIMIT 1"
    )
    if not rows:
        return {}
    r = rows[0]
    vix = r[1]
    regime_raw = r[15]
    sub = r[16]

    regime_display = {
        "complacent": "COMPLACENT",
        "hedged_orderly": "HEDGED-ORDERLY" if sub == "normal" else "HEDGED-FEAR",
        "panic": "PANIC",
    }.get(regime_raw, "UNKNOWN")

    color = {"complacent": "green", "hedged_orderly": "amber", "panic": "red"}.get(regime_raw, "gray")
    if sub == "fear":
        color = "red"

    term_str = r[13]

    return {
        "regime": regime_display, "regimeColor": color,
        "timestamp": str(r[0]) + " ET",
        "vixLevel": vix,
        "kpis": _build_kpis(r),
        "signals": _build_signals(r),
        "termStructure": _build_term_structure(vix),
    }

def get_history(days: int = 30) -> dict:
    rows = db.execute(
        f"SELECT date, vix_spot, spx_close, implied_realized_spread FROM vol_regime_daily FINAL "
        f"ORDER BY date DESC LIMIT {days}"
    )
    rows = list(reversed(rows))
    from datetime import datetime
    fmt = lambda d: datetime.strptime(str(d), "%Y-%m-%d").strftime("%b %-d")
    return {
        "vixSeries":     [{"date": fmt(r[0]), "value": r[1]} for r in rows],
        "spxSeries":     [{"date": fmt(r[0]), "value": r[2]} for r in rows],
        "implRealSeries": [{"date": fmt(r[0]), "value": r[3]} for r in rows],
    }

def generate_note() -> str:
    latest = get_latest_regime()
    # Template-based note (LLM enhancement handled separately)
    regime = latest.get("regime", "UNKNOWN")
    vix = latest.get("vixLevel", 0)
    kpis = {k["label"]: k["value"] for k in latest.get("kpis", [])}
    term = kpis.get("Term Structure", "Contango")
    spread = kpis.get("Impl/Real Spread", "0")
    move = kpis.get("MOVE Index", "0")
    oil = kpis.get("WTI Crude", "0")
    return (
        f"{regime} REGIME | VIX {vix:.2f} — Volatility environment is {regime.lower().replace('-', ' ')}. "
        f"Term structure in {term.lower()}. Implied-Realized spread at {spread}. "
        f"MOVE Index at {move}. WTI crude at {oil}. "
        f"Adjust position sizing and strategy selection accordingly."
    )

def _get_spx_closes_25() -> list:
    """Get last 25 SPX closes from ClickHouse ohlcv_5m or yfinance."""
    try:
        rows = db.execute(
            "SELECT toDate(ts) as d, argMax(close, ts) as c FROM ohlcv_5m "
            "WHERE symbol='SPY' GROUP BY d ORDER BY d DESC LIMIT 25"
        )
        if len(rows) >= 20:
            return [float(r[1]) for r in reversed(rows)]
    except Exception:
        pass
    import yfinance as yf
    hist = yf.Ticker("^GSPC").history(period="30d")
    return list(hist["Close"].values[-25:])

def _build_kpis(r) -> list:
    return [
        {"label": "VIX Spot",       "value": f"{r[1]:.2f}",   "delta": f"{r[2]:+.2f}",  "deltaPct": f"{r[3]:+.2f}%", "positive": r[2] < 0},
        {"label": "S&P 500",        "value": f"{r[4]:,.2f}",  "delta": f"{r[5]:+.2f}",  "deltaPct": f"{r[5]:+.2f}%", "positive": r[5] > 0},
        {"label": "WTI Crude",      "value": f"{r[6]:.2f}",   "delta": f"{r[7]:+.2f}",  "deltaPct": f"{r[7]:+.2f}%", "positive": r[7] > 0},
        {"label": "MOVE Index",     "value": f"{r[8]:.1f}",   "delta": f"{r[9]:+.2f}",  "deltaPct": f"{r[9]:+.2f}%", "positive": r[9] < 0},
        {"label": "VIXY",           "value": f"{r[10]:.2f}",  "delta": "",               "deltaPct": "",              "positive": False},
        {"label": "20d Real Vol",   "value": f"{r[11]:.1f}%", "delta": "",               "deltaPct": "",              "positive": True},
        {"label": "Impl/Real Spread","value": f"{r[12]:.1f} pts","delta": "",             "deltaPct": "",              "positive": False},
        {"label": "Term Structure", "value": r[13].capitalize(),"delta": "",             "deltaPct": "",              "positive": r[13] == "contango"},
    ]

def _build_signals(r) -> list:
    vix, ts, spread, move = r[1], r[13], r[12], r[8]
    return [
        {"name": "VIX Level",        "status": "red" if vix > 25 else "amber" if vix > 15 else "green", "value": f"{vix:.2f}", "note": "Above 15 threshold" if vix > 15 else "Complacent"},
        {"name": "VIX 1-Day Change", "status": "amber" if abs(r[3]) > 5 else "green", "value": f"{r[2]:+.2f}", "note": "Manageable move" if abs(r[3]) < 5 else "Large spike"},
        {"name": "Term Structure",   "status": "red" if ts == "backwardation" else "green", "value": ts.capitalize(), "note": "Normal carry" if ts == "contango" else "Stress signal"},
        {"name": "Impl-Real Spread", "status": "amber" if spread > 3 else "green", "value": f"{spread:.1f} pts", "note": "Elevated premium" if spread > 3 else "Normal"},
        {"name": "MOVE Index",       "status": "red" if move > 120 else "amber" if move > 90 else "green", "value": f"{move:.1f}", "note": "Below 110 alert" if move < 110 else "Elevated"},
        {"name": "Oil (WTI)",        "status": "amber" if abs(r[7]) > 2 else "green", "value": f"${r[6]:.2f}", "note": "Near support"},
    ]

def _build_term_structure(vix_spot: float) -> list:
    """Approximate VIX term structure from spot (real data requires VIX futures)."""
    tenors = ["Spot", "1M", "2M", "3M", "6M", "1Y"]
    premiums = [0, 0.037, 0.074, 0.101, 0.146, 0.185]  # typical contango premia
    return [{"tenor": t, "value": round(vix_spot * (1 + p), 2)} for t, p in zip(tenors, premiums)]