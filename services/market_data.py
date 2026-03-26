"""
Unified market data service. Fallback chain: Polygon → FMP → yfinance.
"""
import httpx
import yfinance as yf
import logging
from config import settings

def get_quote(ticker: str) -> dict:
    """Fetch single quote. Returns dict with keys: price, change, change_pct, volume."""
    if settings.POLYGON_API_KEY:
        try:
            return _polygon_quote(ticker)
        except Exception as e:
            logging.warning(f"Polygon failed for {ticker}: {e}")
    if settings.FMP_API_KEY:
        try:
            return _fmp_quote(ticker)
        except Exception as e:
            logging.warning(f"FMP failed for {ticker}: {e}")
    return _yfinance_quote(ticker)

def get_quotes_batch(tickers: list) -> dict:
    """Fetch multiple quotes. Returns {ticker: quote_dict}."""
    if settings.POLYGON_API_KEY:
        try:
            return _polygon_batch(tickers)
        except Exception as e:
            logging.warning(f"Polygon batch failed: {e}")
    # yfinance batch download
    data = yf.download(tickers, period="2d", interval="1d", progress=False)
    result = {}
    for t in tickers:
        try:
            closes = data["Close"][t].dropna()
            if len(closes) >= 2:
                price = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2])
                result[t] = {"price": price, "change": price - prev, "change_pct": (price - prev) / prev * 100}
        except Exception:
            pass
    return result

def get_history(ticker: str, period_days: int = 30) -> list:
    """Fetch daily close history. Returns [{date, close}]."""
    df = yf.Ticker(ticker).history(period=f"{period_days + 10}d")
    return [
        {"date": row.Index.strftime("%b %-d"), "value": float(row.Close)}
        for row in df.itertuples()
    ][-period_days:]

def _polygon_quote(ticker: str) -> dict:
    url = f"https://api.polygon.io/v2/last/trade/{ticker.replace('^', '')}"
    r = httpx.get(url, params={"apiKey": settings.POLYGON_API_KEY}, timeout=5)
    r.raise_for_status()
    d = r.json()["results"]
    return {"price": d["p"], "change": 0, "change_pct": 0}

def _polygon_batch(tickers: list) -> dict:
    symbols = ",".join([t.replace("^", "") for t in tickers])
    url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
    r = httpx.get(url, params={"tickers": symbols, "apiKey": settings.POLYGON_API_KEY}, timeout=10)
    r.raise_for_status()
    result = {}
    for item in r.json().get("tickers", []):
        t = item["ticker"]
        day = item.get("day", {})
        result[t] = {
            "price": item.get("lastTrade", {}).get("p", day.get("c", 0)),
            "change": day.get("c", 0) - day.get("o", 0),
            "change_pct": item.get("todaysChangePerc", 0),
        }
    return result

def _fmp_quote(ticker: str) -> dict:
    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
    r = httpx.get(url, params={"apikey": settings.FMP_API_KEY}, timeout=5)
    r.raise_for_status()
    d = r.json()[0]
    return {"price": d["price"], "change": d["change"], "change_pct": d["changesPercentage"]}

def _yfinance_quote(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="2d")
    if len(hist) >= 2:
        price = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-2])
        return {"price": price, "change": price - prev, "change_pct": (price - prev) / prev * 100}
    return {"price": 0, "change": 0, "change_pct": 0}