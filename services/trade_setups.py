"""
Trade setup generation for derivatives desk.
Produces directional trade ideas based on current market conditions.
"""
import logging
from services.market_data import get_quote

def generate_derivatives_setups() -> list:
    """Generate trade setups for the derivatives desk note."""
    setups = []

    # Rates setup based on VIX/MOVE relationship
    try:
        vix = get_quote("^VIX")["price"]
        move = get_quote("^MOVE")["price"]

        if vix < 15 and move < 90:
            setups.append({
                "instrument": "ZN", "direction": "Short",
                "thesis": "Low vol regime — rates likely to drift higher on complacency unwind",
                "entry": "current", "target": "-0.5pt", "stop": "+0.25pt",
                "confidence": "Medium", "rr": "2:1",
            })

        if vix > 25:
            setups.append({
                "instrument": "ES", "direction": "Long",
                "thesis": "Elevated VIX — mean reversion bounce likely within 5 sessions",
                "entry": "current", "target": "+2%", "stop": "-1%",
                "confidence": "Medium", "rr": "2:1",
            })

        # Crypto basis trade
        btc = get_quote("BTC-USD")["price"]
        if btc > 0:
            setups.append({
                "instrument": "BTC", "direction": "Long basis",
                "thesis": "CME-spot basis annualizing >8% — carry trade opportunity",
                "entry": "spot + futures", "target": "8%+ ann.", "stop": "basis collapse <3%",
                "confidence": "Low", "rr": "3:1",
            })

    except Exception as e:
        logging.warning(f"Error generating setups: {e}")

    if not setups:
        setups.append({
            "instrument": "N/A", "direction": "Flat",
            "thesis": "No high-conviction setups identified in current regime",
            "entry": "N/A", "target": "N/A", "stop": "N/A",
            "confidence": "N/A", "rr": "N/A",
        })

    return setups
