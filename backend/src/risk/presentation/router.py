from fastapi import APIRouter, Depends

from risk.application.dto import EvaluateLiveRiskRequest, EvaluateRiskRequest, RiskEvaluationResponse, RiskOpenPositionResponse
from risk.application.service import RiskService, get_risk_service

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/evaluate", response_model=RiskEvaluationResponse, summary="Evaluate risk for a strategy signal")
async def evaluate_risk(
    request: EvaluateRiskRequest,
    service: RiskService = Depends(get_risk_service),
) -> RiskEvaluationResponse:
    return service.evaluate_signal(request)


@router.post("/{epic}/evaluate-live", response_model=RiskEvaluationResponse, summary="Evaluate risk for live strategy signal")
async def evaluate_live_risk(
    epic: str,
    request: EvaluateLiveRiskRequest,
    service: RiskService = Depends(get_risk_service),
) -> RiskEvaluationResponse:
    return service.evaluate_live(epic, request)


@router.post("/open-position", response_model=RiskOpenPositionResponse, summary="Open a validated position from a signal")
async def open_validated_position(
    request: EvaluateRiskRequest,
    service: RiskService = Depends(get_risk_service),
) -> RiskOpenPositionResponse:
    return service.open_validated_from_signal(request)


@router.post("/{epic}/open-live-position", response_model=RiskOpenPositionResponse, summary="Open a validated live position")
async def open_validated_live_position(
    epic: str,
    request: EvaluateLiveRiskRequest,
    service: RiskService = Depends(get_risk_service),
) -> RiskOpenPositionResponse:
    return service.open_validated_live(epic, request)
