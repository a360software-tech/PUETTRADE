from fastapi import APIRouter, Depends, Query

from execution.domain.models import ExecutionMode
from portfolio.application.dto import PortfolioPositionsResponse, PortfolioQuery, PortfolioReconciliationResponse
from portfolio.application.service import PortfolioService, get_portfolio_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/positions", response_model=PortfolioPositionsResponse, summary="Get local and provider open positions")
async def get_portfolio_positions(
    execution_mode: ExecutionMode | None = Query(default=None),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioPositionsResponse:
    return await service.get_positions(PortfolioQuery(execution_mode=execution_mode))


@router.get("/reconcile", response_model=PortfolioReconciliationResponse, summary="Reconcile local and provider positions")
async def reconcile_portfolio(
    execution_mode: ExecutionMode | None = Query(default=None),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioReconciliationResponse:
    return await service.reconcile(PortfolioQuery(execution_mode=execution_mode))
