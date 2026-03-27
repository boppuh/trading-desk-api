from fastapi import APIRouter
from services import vol_regime_service, fear_service
from services.market_data import get_quotes_batch
from config import WATCHLIST_25
import db

router = APIRouter()

@router.get("/full")
def get_full_briefing():
    regime = vol_regime_service.get_latest_regime()
    fear = fear_service.get_premarket_fear()
    quotes = get_quotes_batch(WATCHLIST_25)
    universe = [
        {"symbol": t, "price": q.get("price", 0), "changePct": round(q.get("change_pct", 0), 2)}
        for t, q in quotes.items()
    ]
    calendar = _query_calendar()
    earnings = _query_earnings()
    return {
        "regime": regime,
        "fear": fear,
        "universe": universe,
        "calendar": calendar,
        "earnings": earnings,
    }

@router.get("/regime")
def get_regime():
    return vol_regime_service.get_latest_regime()

@router.get("/fear")
def get_fear():
    return fear_service.get_fear_gauges()

@router.get("/universe")
def get_universe():
    quotes = get_quotes_batch(WATCHLIST_25)
    return [
        {"symbol": t, "price": q.get("price", 0), "change": q.get("change", 0),
         "changePct": round(q.get("change_pct", 0), 2)}
        for t, q in quotes.items()
    ]

@router.get("/calendar")
def get_calendar():
    return _query_calendar()

@router.get("/earnings")
def get_earnings():
    return _query_earnings()

def _query_calendar():
    rows = db.execute(
        "SELECT date, time_et, event_name, prior, consensus, actual, impact, surprise "
        "FROM economic_events FINAL WHERE date >= today() ORDER BY date, time_et LIMIT 50"
    )
    return [
        {"date": str(r[0]), "time": r[1], "event": r[2], "prior": r[3],
         "consensus": r[4], "actual": r[5] or "—", "impact": r[6], "surprise": r[7] or ""}
        for r in rows
    ]

def _query_earnings():
    rows = db.execute(
        "SELECT date, symbol, report_time, fiscal_period, eps_estimate, eps_actual, "
        "revenue_estimate, revenue_actual, surprise_pct, price_reaction_pct "
        "FROM earnings_events FINAL WHERE date >= today() ORDER BY date, symbol LIMIT 50"
    )
    return [
        {"date": str(r[0]), "symbol": r[1], "reportTime": r[2], "fiscalPeriod": r[3],
         "epsEstimate": r[4], "epsActual": r[5], "revenueEstimate": r[6],
         "revenueActual": r[7], "surprisePct": r[8], "priceReactionPct": r[9]}
        for r in rows
    ]
