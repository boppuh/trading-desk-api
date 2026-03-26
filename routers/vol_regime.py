from fastapi import APIRouter, Query
from services import vol_regime_service
from config import FORWARD_RETURNS
import db

router = APIRouter()

@router.get("/regime")
async def get_regime():
    return vol_regime_service.get_latest_regime()

@router.get("/history")
async def get_history(days: int = Query(default=30, ge=1, le=365)):
    return vol_regime_service.get_history(days)

@router.get("/events")
async def get_events():
    rows = db.execute(
        "SELECT date, time_et, event, estimate, previous, actual, impact "
        "FROM macro_events FINAL WHERE date >= today() ORDER BY date, time_et LIMIT 50"
    )
    return [
        {"time": r[1], "event": r[2], "prior": r[4], "consensus": r[3], "actual": r[5] or "—", "impact": r[6]}
        for r in rows
    ]

@router.get("/note")
async def get_note():
    return {"text": vol_regime_service.generate_note()}

@router.get("/forward-returns")
async def get_forward_returns():
    return [
        {"regime": v["label"], "1d": f"{v['1d']:+.2f}%", "5d": f"{v['5d']:+.2f}%", "20d": f"{v['20d']:+.2f}%", "n": v["n"]}
        for v in FORWARD_RETURNS.values()
    ]