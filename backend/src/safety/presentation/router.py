from fastapi import APIRouter, Depends, Query

from execution.domain.models import ExecutionMode
from safety.application.dto import RegisterTradeRequest, SafetyQuery, SafetyResponse
from safety.application.service import SafetyService, get_safety_service

router = APIRouter(prefix="/safety", tags=["safety"])


@router.get("/status", response_model=SafetyResponse, summary="Get operational safety status")
async def get_safety_status(
    epic: str | None = Query(default=None),
    execution_mode: ExecutionMode | None = Query(default=None),
    service: SafetyService = Depends(get_safety_service),
) -> SafetyResponse:
    return SafetyResponse(report=await service.evaluate(SafetyQuery(epic=epic, execution_mode=execution_mode)))


@router.post("/register-trade", response_model=SafetyResponse, summary="Register a trade for grace period and cooldown")
async def register_trade(
    request: RegisterTradeRequest,
    service: SafetyService = Depends(get_safety_service),
) -> SafetyResponse:
    service.register_trade_execution(request)
    return SafetyResponse(report=await service.evaluate(SafetyQuery(epic=request.epic)))
