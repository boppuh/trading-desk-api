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

def create_all_tables():
    """Run this once to create all tables."""
    from db import get_client
    client = get_client()
    for name, ddl in TABLES.items():
        client.execute(ddl)
        print(f"Created table: {name}")

if __name__ == "__main__":
    create_all_tables()