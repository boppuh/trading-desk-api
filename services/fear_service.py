"""
Fear & macro gauge service. Shared between premarket and cockpit dashboards.
Sources: FMP (VIX, MOVE), FRED (HY OAS), CNN Money (Fear & Greed), AAII, NAAIM
"""
import httpx
import logging
from config import settings
from services.market_data import get_quote

def get_fear_gauges() -> list:
    """Returns 7 fear gauge dicts matching cockpitData.fearGauges shape."""
    vix = get_quote("^VIX")["price"]
    move = get_quote("^MOVE")["price"]
    term_sprd = _get_vix_term_spread(vix)
    cnn_fg = _fetch_cnn_fear_greed()
    aaii_bull = _fetch_aaii_bull_pct()
    naaim = _fetch_naaim_exposure()
    hy_oas = _fetch_hy_oas()

    def color(name, value):
        # For most gauges: low=green, mid=amber, high=red (higher = more stress)
        # For Fear & Greed: scale is inverted (low=fear=red, high=greed=green)
        # For VIX Term Spread: negative=backwardation=red, positive=contango=green
        thresholds = {
            "VIX": (15, 25), "MOVE": (90, 120),
            "HY OAS": (300, 450),
            "AAII Bull%": (35, 55), "NAAIM Exp.": (50, 100),
        }
        inverted = {
            "Fear & Greed": (30, 50),      # <=30 extreme fear (red), >=50 neutral+ (green)
            "VIX Term Sprd": (-1, 2),      # negative=backwardation (red), >2=contango (green)
        }
        if name in inverted:
            lo, hi = inverted[name]
            if value <= lo: return "red"
            elif value <= hi: return "amber"
            else: return "green"
        lo, hi = thresholds[name]
        if value <= lo: return "green"
        elif value <= hi: return "amber"
        else: return "red"

    return [
        {"name": "VIX",          "value": vix,      "min": 0,    "max": 50,  "threshold": 20,  "unit": "",    "color": color("VIX", vix)},
        {"name": "MOVE",         "value": move,     "min": 50,   "max": 200, "threshold": 120, "unit": "",    "color": color("MOVE", move)},
        {"name": "Fear & Greed", "value": cnn_fg,   "min": 0,    "max": 100, "threshold": 40,  "unit": "",    "color": color("Fear & Greed", cnn_fg)},
        {"name": "AAII Bull%",   "value": aaii_bull,"min": 0,    "max": 100, "threshold": 35,  "unit": "%",   "color": color("AAII Bull%", aaii_bull)},
        {"name": "NAAIM Exp.",   "value": naaim,    "min": 0,    "max": 200, "threshold": 100, "unit": "",    "color": color("NAAIM Exp.", naaim)},
        {"name": "HY OAS",       "value": hy_oas,   "min": 200,  "max": 800, "threshold": 450, "unit": "bps", "color": color("HY OAS", hy_oas)},
        {"name": "VIX Term Sprd","value": term_sprd,"min": -3,   "max": 5,   "threshold": 2,   "unit": "",    "color": color("VIX Term Sprd", term_sprd)},
    ]

def get_premarket_fear() -> dict:
    gauges = get_fear_gauges()
    g = {item["name"]: item for item in gauges}
    vix, move = g["VIX"]["value"], g["MOVE"]["value"]
    fg = g["Fear & Greed"]["value"]
    assessment = _generate_assessment(vix, move, fg)
    return {
        "vix":      {"value": vix,   "regime": _regime_label("VIX", vix),       "color": g["VIX"]["color"]},
        "move":     {"value": move,  "regime": _regime_label("MOVE", move),      "color": g["MOVE"]["color"]},
        "fearGreed":{"value": fg,    "regime": _regime_label("Fear & Greed", fg),"color": g["Fear & Greed"]["color"]},
        "aaii":     {"value": f"{g['AAII Bull%']['value']:.0f}% Bull", "regime": "Mildly Bullish", "color": g["AAII Bull%"]["color"]},
        "naaim":    {"value": g["NAAIM Exp."]["value"], "regime": "Elevated Exposure" if g["NAAIM Exp."]["value"] > 75 else "Normal", "color": g["NAAIM Exp."]["color"]},
        "hyOas":    {"value": f"{g['HY OAS']['value']:.0f} bps", "regime": "Tight" if g["HY OAS"]["value"] < 350 else "Wide", "color": g["HY OAS"]["color"]},
        "assessment": assessment,
    }

def _get_vix_term_spread(vix_spot: float) -> float:
    vixy = get_quote("VIXY")["price"]
    return round((vixy - vix_spot) / vix_spot * 100, 2)

def _fetch_cnn_fear_greed() -> float:
    try:
        r = httpx.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", timeout=5)
        return float(r.json()["fear_and_greed"]["score"])
    except Exception:
        return 50.0  # neutral fallback

def _fetch_aaii_bull_pct() -> float:
    """AAII publishes weekly sentiment. Returns bull % from latest week.
    Stub — AAII XLS parsing not yet implemented."""
    return 41.3

def _fetch_naaim_exposure() -> float:
    """NAAIM Exposure Index — manager equity allocation 0-200."""
    return 78.4  # Stub — NAAIM requires parsing weekly PDF/table at naaim.org

def _fetch_hy_oas() -> float:
    """High-yield option-adjusted spread from FRED BAMLH0A0HYM2."""
    try:
        if not settings.FRED_API_KEY:
            return 312.0
        r = httpx.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": "BAMLH0A0HYM2", "api_key": settings.FRED_API_KEY,
                    "limit": 1, "sort_order": "desc", "file_type": "json"},
            timeout=5
        )
        obs = r.json()["observations"]
        return float(obs[0]["value"]) if obs else 312.0
    except Exception:
        return 312.0

def _regime_label(name, value) -> str:
    labels = {
        "VIX": [(15, "Complacent"), (25, "Hedged-Orderly"), (float("inf"), "Panic")],
        "MOVE": [(90, "Calm"), (120, "Elevated"), (float("inf"), "Stressed")],
        "Fear & Greed": [(30, "Extreme Fear"), (50, "Neutral"), (70, "Greed"), (float("inf"), "Extreme Greed")],
    }
    for threshold, label in labels.get(name, [(float("inf"), "Normal")]):
        if value <= threshold:
            return label
    return "Normal"

def _generate_assessment(vix, move, fg) -> str:
    if vix > 25 or move > 120:
        return "Risk environment is ELEVATED. Position defensively. VIX/MOVE signals stress."
    elif vix < 15 and fg > 60:
        return "Risk environment is COMPLACENT. Consider trimming. Complacency at elevated levels."
    else:
        return "Risk environment is HEDGED-ORDERLY. Complacency building but not extreme. Tactical risk-taking is appropriate with defined stops."
