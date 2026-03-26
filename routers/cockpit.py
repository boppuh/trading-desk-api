from fastapi import APIRouter, Query
from services.gex_service import get_gex, get_dark_pool_prints, run_watchlist_scanner
from services.fear_service import get_fear_gauges
from services.trade_setups import generate_cockpit_setups

router = APIRouter()

@router.get("/gex")
def gex(ticker: str = Query(default="SPY")):
    return get_gex(ticker.upper())

@router.get("/darkpool")
def darkpool():
    return get_dark_pool_prints()

@router.get("/fear")
def fear():
    return get_fear_gauges()

@router.get("/scanner")
def scanner():
    return run_watchlist_scanner()

@router.get("/setups")
def setups():
    return generate_cockpit_setups()
