from fastapi import APIRouter, Depends

from risk.application.dto import EvaluateLiveRiskRequest, EvaluateRiskRequest, RiskEvaluationResponse
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
