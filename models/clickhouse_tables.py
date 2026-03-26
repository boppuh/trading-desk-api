"""
ClickHouse table definitions for the trading desk API.
Run this file once to create all tables.
"""

TABLES = {}

TABLES["vol_regime_daily"] = """
CREATE TABLE IF NOT EXISTS vol_regime_daily (
    date                    Date,
    vix_spot                Float64,
    vix_change              Float64,
    vix_change_pct          Float64,
    spx_close               Float64,
    spx_change_pct          Float64,
    oil_wti                 Float64,
    oil_change_pct          Float64,
    move_index              Float64,
    move_change_pct         Float64,
    vixy_close              Float64,
    realized_vol_20d        Float64,
    implied_realized_spread Float64,
    term_structure_state    String,
    term_structure_spread_pct Float64,
    regime                  String,
    sub_regime              String,
    composite_score         Float64
) ENGINE = ReplacingMergeTree()
ORDER BY date
"""

TABLES["macro_events"] = """
CREATE TABLE IF NOT EXISTS macro_events (
    date        Date,
    time_et     String,
    event       String,
    estimate    String,
    previous    String,
    actual      String DEFAULT '',
    impact      String
) ENGINE = ReplacingMergeTree()
ORDER BY (date, time_et, event)
"""

TABLES["daily_snapshots"] = """
CREATE TABLE IF NOT EXISTS daily_snapshots (
    date Date, spx_close Float64, qqq_close Float64, iwm_close Float64, dia_close Float64,
    vix_close Float64, vix_change_pct Float64, term_structure String, put_call_ratio Float64,
    hyg_close Float64, tlt_close Float64, uso_close Float64, gld_close Float64,
    regime_label String, regime_color String, regime_assessment String, created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree() ORDER BY date
"""

TABLES["universe_snapshots"] = """
CREATE TABLE IF NOT EXISTS universe_snapshots (
    date Date, symbol String, price Float64, change_pct Float64, volume Int64,
    avg_volume Int64, volume_ratio Float64, day_high Float64, day_low Float64,
    prev_close Float64, signal String
) ENGINE = ReplacingMergeTree() ORDER BY (date, symbol)
"""

TABLES["options_flow"] = """
CREATE TABLE IF NOT EXISTS options_flow (
    date Date, symbol String, expiration Date, strike Float64, option_type String,
    volume Int32, open_interest Int32, vol_oi_ratio Float64, implied_vol Float64,
    sentiment String, premium Float64, flow_type String
) ENGINE = ReplacingMergeTree() ORDER BY (date, symbol, expiration, strike, option_type)
"""

TABLES["trade_setups"] = """
CREATE TABLE IF NOT EXISTS trade_setups (
    date Date, session String, symbol String, setup_name String, direction String,
    thesis String, entry Float64, target Float64, stop Float64, rr_ratio Float64,
    score Int32, confidence String, result String DEFAULT 'open', actual_pnl_bps Int32 DEFAULT 0
) ENGINE = ReplacingMergeTree() ORDER BY (date, session, symbol, setup_name)
"""

TABLES["earnings_events"] = """
CREATE TABLE IF NOT EXISTS earnings_events (
    date Date, symbol String, report_time String, fiscal_period String,
    eps_estimate Float64, eps_actual Float64, revenue_estimate Int64, revenue_actual Int64,
    surprise_pct Float64, price_reaction_pct Float64
) ENGINE = ReplacingMergeTree() ORDER BY (date, symbol)
"""

TABLES["economic_events"] = """
CREATE TABLE IF NOT EXISTS economic_events (
    date Date, time_et String, event_name String, prior String, consensus String,
    actual String DEFAULT '', impact String, surprise String DEFAULT ''
) ENGINE = ReplacingMergeTree() ORDER BY (date, time_et, event_name)
"""

TABLES["fear_snapshots"] = """
CREATE TABLE IF NOT EXISTS fear_snapshots (
    date Date, session String, vix Float64, vix_change Float64, term_structure_state String,
    move_index Float64, hy_oas_proxy Float64, tlt_price Float64, uso_price Float64,
    gld_price Float64, cnn_fear_greed Float64, aaii_bull_pct Float64,
    naaim_exposure Float64, regime_assessment String
) ENGINE = ReplacingMergeTree() ORDER BY (date, session)
"""

TABLES["commodity_snapshots"] = """
CREATE TABLE IF NOT EXISTS commodity_snapshots (
    timestamp DateTime, symbol String, price Float64, change Float64, pct_change Float64,
    open Float64, high Float64, low Float64, volume Int64
) ENGINE = ReplacingMergeTree() ORDER BY (timestamp, symbol) PARTITION BY toYYYYMM(timestamp)
"""

TABLES["crack_spreads"] = """
CREATE TABLE IF NOT EXISTS crack_spreads (
    timestamp DateTime, spread_321 Float64, jet_crack_approx Float64, diesel_crack Float64
) ENGINE = ReplacingMergeTree() ORDER BY timestamp PARTITION BY toYYYYMM(timestamp)
"""

TABLES["supply_shocks"] = """
CREATE TABLE IF NOT EXISTS supply_shocks (
    timestamp DateTime, headline String, severity String, severity_color String,
    summary String, affected_tickers String, source_url String, tags String
) ENGINE = ReplacingMergeTree() ORDER BY (timestamp, headline)
"""

TABLES["hormuz_transits"] = """
CREATE TABLE IF NOT EXISTS hormuz_transits (
    date Date, transit_count Float64, vessels_trapped Int32, attacks_mtd Int32, status String
) ENGINE = ReplacingMergeTree() ORDER BY date
"""

TABLES["exposure_rankings"] = """
CREATE TABLE IF NOT EXISTS exposure_rankings (
    timestamp DateTime, symbol String, direction String, score Float64, thesis String, sector String
) ENGINE = ReplacingMergeTree() ORDER BY (timestamp, symbol)
"""

TABLES["desk_notes"] = """
CREATE TABLE IF NOT EXISTS desk_notes (
    trade_date Date, scoreboard String, rates_data String, vol_data String,
    crypto_data String, setups String, macro_context String, created_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree() ORDER BY trade_date
"""

TABLES["gex_levels"] = """
CREATE TABLE IF NOT EXISTS gex_levels (
    date Date, underlying String, strike Float64,
    call_gex Float64, put_gex Float64, net_gex Float64,
    call_wall UInt8, put_wall UInt8, zero_gamma UInt8
) ENGINE = ReplacingMergeTree() ORDER BY (date, underlying, strike)
"""

def create_all_tables():
    """Run this once to create all tables."""
    from db import get_client
    client = get_client()
    for name, ddl in TABLES.items():
        client.execute(ddl)
        print(f"Created table: {name}")

if __name__ == "__main__":
    create_all_tables()