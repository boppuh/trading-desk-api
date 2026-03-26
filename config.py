from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    POLYGON_API_KEY: str = ""
    FMP_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DATABENTO_API_KEY: str = ""
    UNUSUAL_WHALES_KEY: str = ""
    NEWS_API_KEY: str = ""
    FRED_API_KEY: str = ""

    # ClickHouse
    CH_HOST: str = "127.0.0.1"
    CH_PORT: int = 9000
    CH_DATABASE: str = "default"
    CH_USER: str = "default"
    CH_PASSWORD: str = ""

    # Server
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3100,http://localhost:3000"
    LOG_LEVEL: str = "INFO"

    # Feature flags
    USE_LLM: bool = False
    GAMMA_SOURCE: str = "stub"
    DARK_POOL_SOURCE: str = "stub"

    class Config:
        env_file = ".env"


settings = Settings()

# Vol regime instruments
VOL_INSTRUMENTS = ["^VIX", "^GSPC", "CL=F", "^MOVE", "VIXY", "UVXY", "SVXY"]

# MSM 25-symbol universe
WATCHLIST_25 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "BRK-B", "LLY", "V",
    "JPM", "WMT", "UNH", "XOM", "MA",
    "PG", "COST", "HD", "JNJ", "NFLX",
    "BAC", "CRM", "AMD", "ORCL", "ABBV",
]

# Derivatives 12-instrument universe
DERIVATIVES_12 = ["ZT", "ZF", "ZN", "ZB", "ES", "NQ", "RTY", "VX", "MOVE", "DXY", "BTC", "ETH"]

# Energy tickers (19 energy + 4 airlines)
ENERGY_TICKERS = [
    "XOM", "CVX", "COP", "EOG", "PXD",
    "SLB", "HAL", "BKR", "PSX", "VLO",
    "MPC", "KMI", "ET", "WMB", "OKE",
    "DVN", "FANG", "OXY", "MRO",
    "AAL", "DAL", "UAL", "LUV",
]

# Historical forward returns (pre-computed, 2006-2026)
FORWARD_RETURNS = {
    "complacent":    {"1d": 0.05, "5d": 0.25,  "20d": 1.00, "n": 1858, "label": "Complacent (VIX <15)"},
    "hedged_normal": {"1d": 0.04, "5d": 0.20,  "20d": 1.20, "n": 2252, "label": "Normal (15-25)"},
    "hedged_fear":   {"1d": -0.05, "5d": -0.10, "20d": -0.30, "n": 413, "label": "Fear (25-30)"},
    "panic":         {"1d": 0.15, "5d": 1.20,  "20d": 3.00, "n": 435,  "label": "Panic (30+)"},
}
