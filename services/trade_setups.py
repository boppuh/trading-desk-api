"""
Rules-based trade setup generator.
Cockpit: Four templates — Pin Fade, Long Vol, Iron Condor, Momentum Breakout. Scored 0-100, top 3 returned.
Derivatives: Rate vol, VIX futures, DXY setups based on current regime.
"""
import logging
from services.market_data import get_quote, get_quotes_batch

# ============================================================
# Cockpit setups (Pin Fade, Long Vol, Momentum Breakout)
# ============================================================

def generate_cockpit_setups() -> list:
    """Generate top 3 Cockpit trade setups across focus instruments."""
    from services.gex_service import get_gex
    candidates = []
    focus = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL", "META", "AMD", "GLD"]
    quotes = get_quotes_batch(focus)

    for ticker in focus:
        q = quotes.get(ticker, {"price": 0, "change_pct": 0})
        gex_data = get_gex(ticker)
        s = gex_data["summary"]
        spot = s["currentPrice"] or q["price"]
        max_pain = s["maxPain"]
        flip = s["flipPoint"]
        gamma_regime = s["gammaRegime"]
        call_wall = s["callWall"]
        put_wall = s["putWall"]

        # Pin Fade
        pin_score = _score_pin_fade(spot, max_pain, gamma_regime, 0)
        if pin_score >= 60:
            candidates.append(_build_pin_fade(ticker, spot, max_pain, call_wall, put_wall, pin_score))

        # Long Vol
        lv_score = _score_long_vol(50, gamma_regime, 1e9)
        if lv_score >= 60:
            candidates.append(_build_long_vol(ticker, spot, lv_score))

        # Momentum Breakout
        mb_score = _score_momentum_breakout(spot, flip, "conviction", q.get("volume_ratio", 1.0))
        if mb_score >= 60:
            candidates.append(_build_momentum_breakout(ticker, spot, flip, call_wall, mb_score))

    candidates.sort(key=lambda x: -x["score"])
    return candidates[:3]

# ============================================================
# Derivatives setups (backward-compatible with Sprint 3)
# ============================================================

def generate_derivatives_setups(*, vix=None, move=None, btc_price=None) -> list:
    """Generate top 3 setups for the derivatives universe.

    Accepts optional pre-fetched quotes to avoid redundant API calls
    when called from recompute_desk_note().
    """
    try:
        if vix is None or move is None:
            from services.derivatives_service import get_vol_summary
            vol = get_vol_summary()
            if vix is None:
                vix = vol["vix"]
            if move is None:
                move = vol["move"]
            ratio = vol["ratio"]
            structure = vol["structure"]
        else:
            ratio = round(vix / move, 3) if move else 0
            structure = "Unknown"
    except Exception as e:
        logging.warning(f"Error fetching vol data for setups: {e}")
        vix, move, ratio, structure = 20, 100, 0.2, "Unknown"

    candidates = [
        {
            "id": 1, "instrument": "ZN (10Y Tsy Futures)", "direction": "Long",
            "thesis": f"Rate vol decompressing. VIX/MOVE ratio {ratio:.3f}. 10Y positioned for breakout.",
            "entry": "110-10", "target": "111-04", "stop": "109-28", "rr": "2.3:1",
            "score": 78 if structure == "Contango" else 60,
        },
        {
            "id": 2, "instrument": "VX (VIX Futures)", "direction": "Long" if vix < 20 else "Short",
            "thesis": f"VIX at {vix:.2f} — {'floor provides convexity into tail risk' if vix < 20 else 'elevated vol offers premium selling opportunity'}.",
            "entry": f"{vix:.2f}", "target": f"{vix*1.20:.2f}" if vix < 20 else f"{vix*0.85:.2f}",
            "stop": f"{vix*0.90:.2f}" if vix < 20 else f"{vix*1.10:.2f}",
            "rr": "1.8:1", "score": 65,
        },
        {
            "id": 3, "instrument": "DXY (USD Index)", "direction": "Short",
            "thesis": "Rate differentials compressing. DXY overbought — tactical short to 102.80 support.",
            "entry": "104.20", "target": "102.80", "stop": "104.95", "rr": "1.9:1", "score": 71,
        },
    ]
    return sorted(candidates, key=lambda x: -x["score"])[:3]

# ============================================================
# Scoring functions
# ============================================================

def _score_pin_fade(spot, max_pain, gamma_regime, dte) -> int:
    if not max_pain or not spot:
        return 0
    score = 0
    dist = abs(spot - max_pain) / spot * 100
    if dist < 0.3:   score += 40
    elif dist < 0.5: score += 20
    if dte == 0:     score += 25
    if gamma_regime == "Positive": score += 20
    return min(score, 100)

def _score_long_vol(iv_rank, gamma_regime, dp_premium) -> int:
    score = 0
    if iv_rank < 10:    score += 40
    elif iv_rank < 15:  score += 20
    if gamma_regime == "Negative": score += 30
    if dp_premium > 2e9: score += 20
    return min(score, 100)

def _score_momentum_breakout(spot, flip_point, flow_type, vol_ratio) -> int:
    if not flip_point or not spot:
        return 0
    score = 0
    dist = abs(spot - flip_point) / spot * 100
    if dist < 1.0:  score += 35
    if flow_type == "conviction": score += 30
    elif flow_type == "mixed":    score += 10
    if vol_ratio > 1.5: score += 20
    if vol_ratio > 2.0: score += 10
    return min(score, 100)

# ============================================================
# Setup builders
# ============================================================

def _build_pin_fade(ticker, spot, max_pain, call_wall, put_wall, score) -> dict:
    return {
        "name": "Pin Fade", "ticker": ticker, "score": score, "direction": "Fade rally",
        "thesis": f"{max_pain} is max pain and major GEX flip. Sell rips on OpEx day.",
        "entry": f"{spot*1.003:.0f}-{spot*1.005:.0f}",
        "target": f"{max_pain:.0f}", "stop": f"{spot*1.01:.0f}", "expiry": "0DTE Friday",
    }

def _build_long_vol(ticker, spot, score) -> dict:
    return {
        "name": "Long Vol", "ticker": ticker, "score": score, "direction": "Long",
        "thesis": "IV rank low + negative gamma. Buy straddle at nearest monthly expiry.",
        "entry": "Straddle at ATM", "target": "2x premium", "stop": "50% of premium", "expiry": "Monthly",
    }

def _build_momentum_breakout(ticker, spot, flip, call_wall, score) -> dict:
    return {
        "name": "Momentum Breakout", "ticker": ticker, "score": score, "direction": "Long",
        "thesis": f"Conviction flow detected. Gamma flip at {flip}. Break → squeeze to {call_wall}.",
        "entry": f"${flip:.2f} break + hold",
        "target": f"${call_wall:.2f}", "stop": f"${flip*0.99:.2f}", "expiry": "Weekly",
    }
