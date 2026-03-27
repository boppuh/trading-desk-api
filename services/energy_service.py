"""
Energy dashboard service — commodity quotes, crack spreads, exposure scoring.
"""
import logging
from datetime import datetime
from services.market_data import get_quotes_batch
from config import ENERGY_TICKERS
import db

COMMODITY_SYMBOLS = {
    "BZ=F": "Brent Crude",
    "CL=F": "WTI Crude",
    "NG=F": "Henry Hub Gas",
    "RB=F": "RBOB Gasoline",
    "HO=F": "Heating Oil",
}

WTI_FALLBACK = 70  # default WTI price when data unavailable

def calc_crack_spread(quotes: dict) -> tuple:
    """Compute 3-2-1 crack spread from commodity quotes. Returns (crack_321, rb_per_bbl, ho_per_bbl, wti)."""
    wti = quotes.get("CL=F", {}).get("price", WTI_FALLBACK)
    rb  = quotes.get("RB=F", {}).get("price", 0) * 42
    ho  = quotes.get("HO=F", {}).get("price", 0) * 42
    crack_321 = (2 * rb + 1 * ho - 3 * wti) / 3
    return crack_321, rb, ho, wti

ENERGY_SECTOR_MAP = {
    "XOM": "Integrated", "CVX": "Integrated", "OXY": "Integrated", "MRO": "E&P",
    "COP": "E&P", "EOG": "E&P", "PXD": "E&P", "DVN": "E&P", "FANG": "E&P",
    "SLB": "Services", "HAL": "Services", "BKR": "Services",
    "PSX": "Refining", "VLO": "Refining", "MPC": "Refining",
    "KMI": "Midstream", "ET": "Midstream", "WMB": "Midstream", "OKE": "Midstream",
    "AAL": "Airlines", "DAL": "Airlines", "UAL": "Airlines", "LUV": "Airlines",
}

def get_commodity_strip() -> list:
    quotes = get_quotes_batch(list(COMMODITY_SYMBOLS.keys()))
    result = []
    crack_321, _, _, _ = calc_crack_spread(quotes)

    for sym, name in COMMODITY_SYMBOLS.items():
        q = quotes.get(sym, {"price": 0, "change": 0, "change_pct": 0})
        result.append({
            "name": name, "symbol": sym,
            "price": f"${q['price']:.2f}", "change": f"${q['change']:+.2f}",
            "changePct": f"{q['change_pct']:+.2f}%", "positive": q["change"] >= 0,
            "sparkline": _get_sparkline(sym),
        })
    # Add crack spread as a synthetic entry
    result.append({
        "name": "3-2-1 Crack Spread", "symbol": "CRACK",
        "price": f"${crack_321:.2f}", "change": "$0.00", "changePct": "+0.00%",
        "positive": True, "sparkline": [],
    })
    return result

def get_watchlist() -> list:
    quotes = get_quotes_batch(ENERGY_TICKERS)
    return [
        {"ticker": t, "change": quotes.get(t, {}).get("change_pct", 0), "sector": ENERGY_SECTOR_MAP.get(t, "Energy")}
        for t in ENERGY_TICKERS
    ]

def _get_previous_baselines() -> tuple:
    """Fetch previous day's crack spread and WTI from ClickHouse. Falls back to static defaults."""
    try:
        rows = db.execute(
            "SELECT spread_321 FROM crack_spreads FINAL ORDER BY timestamp DESC LIMIT 1"
        )
        prev_crack = float(rows[0][0]) if rows else 25.0
        wti_rows = db.execute(
            "SELECT price FROM commodity_snapshots WHERE symbol='CL=F' ORDER BY timestamp DESC LIMIT 1 OFFSET 1"
        )
        prev_wti = float(wti_rows[0][0]) if wti_rows else 70.0
        return prev_crack, prev_wti
    except Exception:
        return 25.0, 70.0

def score_exposure() -> list:
    quotes = get_quotes_batch(["CL=F", "HO=F", "RB=F"] + ENERGY_TICKERS)
    crack, rb, ho, wti = calc_crack_spread(quotes)
    prev_crack, prev_wti = _get_previous_baselines()

    scored = []
    for ticker in ENERGY_TICKERS:
        q = quotes.get(ticker, {"price": 0, "change_pct": 0})
        sector = ENERGY_SECTOR_MAP.get(ticker, "Energy")
        score = _exposure_score(sector, crack, wti, prev_crack, prev_wti)
        direction = "Long" if score >= 65 else "Short" if score <= 35 else "Watch"
        thesis = _exposure_thesis(ticker, sector, direction, crack, wti)
        scored.append({
            "ticker": ticker, "price": f"${q['price']:.2f}", "change": f"{q['change_pct']:+.2f}%",
            "sector": sector, "direction": direction, "thesis": thesis, "score": score,
        })

    scored.sort(key=lambda x: -x["score"])
    for i, item in enumerate(scored, 1):
        item["rank"] = i
    return scored[:8]

def _clamp(value, low, high):
    """Clamp value to [low, high] range — caps both positive and negative."""
    return max(low, min(value, high))

def _exposure_score(sector, crack, wti, prev_crack=25.0, prev_wti=70.0) -> int:
    score = 50
    crack_change = crack - prev_crack
    wti_change = wti - prev_wti
    if sector in ("Services", "E&P"):
        score += _clamp(wti_change * 2, -25, 25)
        score += _clamp(crack_change * 1.5, -15, 15)
    elif sector == "Refining":
        score += _clamp(crack_change * 3, -30, 30)
        score -= _clamp(wti_change, -15, 15)
    elif sector == "Airlines":
        score -= _clamp(crack_change * 4, -40, 40)
        score -= _clamp(wti_change * 2, -20, 20)
    elif sector in ("Integrated", "Midstream"):
        score += _clamp(wti_change, -15, 15)
    return max(0, min(100, int(score)))

def _exposure_thesis(ticker, sector, direction, crack, wti) -> str:
    if sector == "Airlines" and direction == "Short":
        return f"Fuel cost headwind + jet fuel crack at ${crack:.0f}/bbl"
    elif sector == "Refining":
        return f"Crack spread at ${crack:.0f}/bbl — watch margin compression"
    elif sector in ("E&P", "Services") and direction == "Long":
        return f"WTI at ${wti:.0f} supports upstream capex and margins"
    return f"{sector} — exposure to crude at ${wti:.0f}/bbl"

def _get_sparkline(symbol: str, days=5) -> list:
    try:
        rows = db.execute(
            "SELECT price FROM commodity_snapshots WHERE symbol=%(s)s "
            "ORDER BY timestamp DESC LIMIT %(d)s",
            {"s": symbol, "d": days}
        )
        return [float(r[0]) for r in reversed(rows)] if rows else []
    except Exception:
        return []
