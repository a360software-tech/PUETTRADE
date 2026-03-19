from pydantic import BaseModel

from execution.domain.models import ExecutionMode
from portfolio.domain.models import PortfolioProviderPosition, PortfolioReconciliationReport
from positions.domain.models import Position


class PortfolioQuery(BaseModel):
    execution_mode: ExecutionMode | None = None


class PortfolioPositionsResponse(BaseModel):
    provider: str
    execution_mode: str
    local_positions: list[Position]
    provider_positions: list[PortfolioProviderPosition]


class PortfolioReconciliationResponse(BaseModel):
    report: PortfolioReconciliationReport
