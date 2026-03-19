from fastapi import APIRouter, Depends, Query

from market_data.application.dto import Resolution

from strategy.application.dto import StrategyEvaluateRequest, StrategyEvaluationResponse
from strategy.application.service import StrategyService, get_strategy_service

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/evaluate", response_model=StrategyEvaluationResponse, summary="Evaluate strategy against candles")
async def evaluate_strategy(
    request: StrategyEvaluateRequest,
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyEvaluationResponse:
    return service.evaluate(request)


@router.get("/{epic}/signal", response_model=StrategyEvaluationResponse, summary="Evaluate live strategy from buffered candles")
async def evaluate_live_strategy(
    epic: str,
    service: StrategyService = Depends(get_strategy_service),
    resolution: Resolution = Query(default="MINUTE_5"),
    limit: int = Query(default=100, ge=5, le=500),
) -> StrategyEvaluationResponse:
    return service.evaluate_live(epic=epic, resolution=resolution, limit=limit)
