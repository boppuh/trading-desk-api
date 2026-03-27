from fastapi import APIRouter, BackgroundTasks
from services import derivatives_service
from services.trade_setups import generate_derivatives_setups

router = APIRouter()

@router.get("/scoreboard")
def scoreboard():
    return derivatives_service.get_scoreboard()

@router.get("/rates")
def rates():
    return derivatives_service.get_rates()

@router.get("/vol")
def vol():
    return derivatives_service.get_vol_summary()

@router.get("/crypto")
def crypto():
    return derivatives_service.get_crypto()

@router.get("/setups")
def setups():
    return generate_derivatives_setups()

@router.get("/desk-note")
def desk_note():
    return derivatives_service.assemble_desk_note()

@router.post("/refresh")
async def refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(derivatives_service.recompute_desk_note)
    return {"status": "triggered", "message": "Recomputing desk note in background"}
