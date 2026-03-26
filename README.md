# Trading Desk API - Vol Regime Dashboard

FastAPI backend for multi-dashboard trading terminal. **Sprint 1 Complete**: Core infrastructure + Vol Regime dashboard.

## Architecture

- **FastAPI** + **ClickHouse** + **APScheduler**
- **Vol Regime Engine**: VIX analysis, term structure, regime classification
- **Market Data**: Polygon → FMP → yfinance fallback chain
- **Premarket Pipeline**: Runs 7:55 AM ET weekdays

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create ClickHouse tables
PYTHONPATH=. python3 models/clickhouse_tables.py

# Start development server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production deployment
sudo cp trading-desk-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trading-desk-api
```

## API Endpoints

### Vol Regime Dashboard

- **GET /api/vol/regime** - Current volatility regime
- **GET /api/vol/history?days=30** - Historical VIX/SPX data  
- **GET /api/vol/events** - Economic calendar
- **GET /api/vol/note** - Premarket regime summary
- **GET /api/vol/forward-returns** - Expected returns by regime

### Health & Status

- **GET /health** - Service health + ClickHouse status

## Configuration

Edit `.env` file:

```bash
# Market data APIs (optional - falls back to yfinance)
POLYGON_API_KEY=your_key
FMP_API_KEY=your_key

# ClickHouse (defaults work for local install)
CH_HOST=127.0.0.1
CH_PORT=9000
CH_DATABASE=default

# Server settings
PORT=8000
CORS_ORIGINS=http://localhost:3100,http://localhost:3000
LOG_LEVEL=INFO
```

## Vol Regime Classification

| VIX Level | Regime | Color | Description |
|-----------|--------|-------|-------------|
| < 15 | **COMPLACENT** | 🟢 Green | Low volatility, bullish |
| 15-25 | **HEDGED-ORDERLY** | 🟡 Amber | Normal volatility |
| 25-30 | **HEDGED-FEAR** | 🔴 Red | Elevated fear |
| 30+ | **PANIC** | 🔴 Red | Crisis mode |

## Data Sources

- **VIX, SPX**: Yahoo Finance (^VIX, ^GSPC)
- **Oil**: WTI Crude (CL=F)
- **Bonds**: MOVE Index (^MOVE)
- **Vol ETFs**: VIXY, UVXY, SVXY

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Current regime
curl http://localhost:8000/api/vol/regime | jq

# Economic events
curl http://localhost:8000/api/vol/events

# Forward returns
curl http://localhost:8000/api/vol/forward-returns
```

## Next Sprint

- **Dark Pool Flow** dashboard
- **Gamma Exposure** analytics
- **Options Flow** monitoring
- **LLM-enhanced** regime notes

---

**Status**: ✅ Sprint 1 Complete  
**Created**: 2026-03-26 by Ghost 👻  
**Stack**: FastAPI + ClickHouse + Vue.js (frontend)