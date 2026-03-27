import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scheduler import start_scheduler, stop_scheduler
from routers import vol_regime, premarket, energy, derivatives, cockpit
from config import settings

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
app.include_router(cockpit.router, prefix="/api/cockpit", tags=["Cockpit"])

class PipelineRequest(BaseModel):
    pipeline: str

@app.post("/api/pipeline/run")
async def run_pipeline(body: PipelineRequest):
    name = body.pipeline
    runners = {
        "energy": lambda: __import__("pipelines.energy_pipeline", fromlist=["run_energy_pipeline"]).run_energy_pipeline,
        "premarket": lambda: __import__("pipelines.premarket_pipeline", fromlist=["run_premarket_pipeline"]).run_premarket_pipeline,
        "close": lambda: __import__("pipelines.close_pipeline", fromlist=["run_close_pipeline"]).run_close_pipeline,
    }
    if name not in runners:
        raise HTTPException(status_code=400, detail=f"Unknown pipeline: {name}")
    try:
        await asyncio.to_thread(runners[name]())
    except Exception as e:
        logging.error(f"Pipeline {name} failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "pipeline": name, "detail": str(e)})
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
