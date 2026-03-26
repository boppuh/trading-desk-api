from fastapi import APIRouter
from services import energy_service
import db

router = APIRouter()

@router.get("/commodities")
async def get_commodities():
    return energy_service.get_commodity_strip()

@router.get("/watchlist")
async def get_watchlist():
    return energy_service.get_watchlist()

@router.get("/exposure")
async def get_exposure():
    return energy_service.score_exposure()

@router.get("/shocks")
async def get_shocks():
    rows = db.execute(
        "SELECT timestamp, headline, severity, severity_color, summary, "
        "affected_tickers, source_url, tags "
        "FROM supply_shocks FINAL ORDER BY timestamp DESC LIMIT 20"
    )
    return [
        {"timestamp": str(r[0]), "headline": r[1], "severity": r[2],
         "severityColor": r[3], "summary": r[4], "affectedTickers": r[5],
         "sourceUrl": r[6], "tags": r[7]}
        for r in rows
    ]

@router.get("/hormuz")
async def get_hormuz():
    rows = db.execute(
        "SELECT date, transit_count, vessels_trapped, attacks_mtd, status "
        "FROM hormuz_transits FINAL ORDER BY date DESC LIMIT 30"
    )
    return [
        {"date": str(r[0]), "transitCount": r[1], "vesselsTrapped": r[2],
         "attacksMtd": r[3], "status": r[4]}
        for r in rows
    ]
