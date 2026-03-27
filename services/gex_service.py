"""
GEX service — wraps databento_gamma.py and the synthesis engine.
"""
import logging
import os
import sys
from config import settings
import db

# Import GEX engine from trader-cockpit if available
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from databento_gamma import DabentoGammaCollector
    GEX_AVAILABLE = True
except ImportError:
    GEX_AVAILABLE = False
    logging.warning("databento_gamma.py not found — GEX will return stub data")

def get_gex(ticker: str = "SPY") -> dict:
    """Get GEX summary + per-strike data for a ticker."""
    if GEX_AVAILABLE and settings.GAMMA_SOURCE == "api" and settings.DATABENTO_API_KEY:
        try:
            collector = DabentoGammaCollector(api_key=settings.DATABENTO_API_KEY)
            result = collector.compute_gex(ticker)
            return {
                "summary": {
                    "ticker": ticker,
                    "netGex": f"${result['net_gex_dollars']:.1f}B",
                    "gammaRegime": result["gamma_regime"],
                    "callWall": result["call_wall"],
                    "putWall": result["put_wall"],
                    "maxPain": result["max_pain"],
                    "flipPoint": result["flip_point"],
                    "currentPrice": result["spot"],
                },
                "strikes": result["per_strike"],
            }
        except Exception as e:
            logging.error(f"GEX compute error: {e}")

    # Fallback: read from ClickHouse gex_levels table
    return _read_gex_from_clickhouse(ticker)

def _read_gex_from_clickhouse(ticker: str) -> dict:
    rows = db.execute(
        "SELECT strike, call_gex, put_gex, net_gex, call_wall, put_wall, zero_gamma "
        "FROM gex_levels WHERE underlying=%(t)s AND date=today() "
        "ORDER BY strike", {"t": ticker}
    )
    if not rows:
        return _stub_gex(ticker)

    strikes = [{"strike": r[0], "callGex": r[1], "putGex": r[2]} for r in rows]
    call_wall = next((r[0] for r in rows if r[4]), 0)
    put_wall  = next((r[0] for r in rows if r[5]), 0)
    flip_point = next((r[0] for r in rows if r[6]), 0)
    net_gex = sum(r[3] for r in rows)

    return {
        "summary": {
            "ticker": ticker, "netGex": f"${net_gex/1e9:.1f}B",
            "gammaRegime": "Positive" if net_gex > 0 else "Negative",
            "callWall": call_wall, "putWall": put_wall,
            "maxPain": flip_point, "flipPoint": flip_point, "currentPrice": 0,
        },
        "strikes": strikes,
    }

def _stub_gex(ticker: str) -> dict:
    """Stub data for development when GEX engine is unavailable."""
    return {
        "summary": {"ticker": ticker, "netGex": "$2.1B", "gammaRegime": "Positive",
                    "callWall": 580, "putWall": 560, "maxPain": 572, "flipPoint": 568, "currentPrice": 572},
        "strikes": [{"strike": 560+i*20, "callGex": 0.3+i*0.3, "putGex": -(1.8-i*0.15)} for i in range(12)],
    }

def get_dark_pool_prints() -> list:
    """Dark pool prints — Unusual Whales API or stub."""
    if settings.DARK_POOL_SOURCE == "api" and settings.UNUSUAL_WHALES_KEY:
        try:
            import httpx
            r = httpx.get(
                "https://api.unusualwhales.com/api/darkpool/recent",
                headers={"Authorization": f"Bearer {settings.UNUSUAL_WHALES_KEY}"},
                timeout=5
            )
            prints = r.json()["data"]
            return [
                {"time": p["executed_at"][-8:-3], "ticker": p["ticker"],
                 "price": f"{float(p['price']):.2f}", "size": f"${float(p['premium'])/1e6:.0f}M",
                 "exchange": "FINRA", "type": "BLOCK" if float(p["premium"]) > 5e6 else "SWEEP"}
                for p in prints[:8] if float(p.get("premium", 0)) > 1e6
            ]
        except Exception as e:
            logging.warning(f"Dark pool API failed: {e}")

    # Fallback: stub data
    return [
        {"time": "09:31:04", "ticker": "SPY",  "price": "571.84", "size": "$847M", "exchange": "FINRA", "type": "BLOCK"},
        {"time": "09:33:22", "ticker": "NVDA", "price": "141.23", "size": "$324M", "exchange": "FINRA", "type": "SWEEP"},
        {"time": "09:41:11", "ticker": "QQQ",  "price": "489.67", "size": "$512M", "exchange": "FINRA", "type": "BLOCK"},
    ]

def run_watchlist_scanner() -> list:
    """Scan for unusual gamma, dark pool spikes, IV extremes, earnings proximity."""
    from config import WATCHLIST_25
    from services.market_data import get_quotes_batch
    quotes = get_quotes_batch(WATCHLIST_25)
    dark_pool = get_dark_pool_prints()
    dp_tickers = {p["ticker"] for p in dark_pool}

    scored = []
    for ticker in WATCHLIST_25:
        q = quotes.get(ticker, {})
        score, signal, reason = _scan_ticker(ticker, q, dp_tickers)
        if score >= 55:
            scored.append({"ticker": ticker, "signal": signal, "score": score, "reason": reason})

    scored.sort(key=lambda x: -x["score"])
    return scored[:10]

def _scan_ticker(ticker, quote, dp_tickers) -> tuple:
    """Return (score, signal_name, reason) for one ticker."""
    score = 40
    signals = []
    reason_parts = []

    # Dark pool presence
    if ticker in dp_tickers:
        score += 25
        signals.append("Dark Pool Alert")
        reason_parts.append("dark pool block detected")

    # Price momentum
    chg = abs(quote.get("change_pct", 0))
    if chg > 3:
        score += 20
        signals.append("Momentum Long" if quote.get("change_pct", 0) > 0 else "Momentum Short")
        reason_parts.append(f"{chg:.1f}% move today")
    elif chg > 1.5:
        score += 10

    signal = " + ".join(signals) if signals else "Watch"
    reason = " + ".join(reason_parts) if reason_parts else "No unusual activity"
    return score, signal, reason
