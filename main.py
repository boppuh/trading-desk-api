import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scheduler import start_scheduler, stop_scheduler
from routers import vol_regime, premarket, energy, derivatives
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
app.include_router(premarket.router, prefix="/api/premarket", tags=["Premarket"])
app.include_router(energy.router, prefix="/api/energy", tags=["Energy"])
app.include_router(derivatives.router, prefix="/api/derivatives", tags=["Derivatives"])

class PipelineRequest(BaseModel):
    pipeline: str

@app.post("/api/pipeline/run")
async def run_pipeline(body: PipelineRequest):
    name = body.pipeline
    if name == "energy":
        from pipelines.energy_pipeline import run_energy_pipeline
        await asyncio.to_thread(run_energy_pipeline)
    elif name == "premarket":
        from pipelines.premarket_pipeline import run_premarket_pipeline
        await asyncio.to_thread(run_premarket_pipeline)
    elif name == "close":
        from pipelines.close_pipeline import run_close_pipeline
        await asyncio.to_thread(run_close_pipeline)
    else:
        return {"error": f"Unknown pipeline: {name}"}
    return {"status": "ok", "pipeline": name}

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