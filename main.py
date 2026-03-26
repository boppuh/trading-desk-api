from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scheduler import start_scheduler, stop_scheduler
from routers import vol_regime
from config import settings
import logging

logging.basicConfig(level=settings.LOG_LEVEL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="Trading Desk API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vol_regime.router, prefix="/api/vol", tags=["Vol Regime"])

@app.get("/health")
async def health():
    from db import get_client
    from scheduler import last_run_times
    try:
        client = get_client()
        client.execute("SELECT 1")
        ch_status = "connected"
    except Exception:
        ch_status = "error"
    return {"status": "ok", "clickhouse": ch_status, "last_pipeline_run": last_run_times}