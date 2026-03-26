from typing import Any

from pydantic import BaseModel, Field

from market_data.application.dto import Resolution
from positions.domain.models import Position
from risk.domain.models import RiskPlan
from strategy.domain.models import StrategyManifest, StrategySignal


class CreatePositionFromSignalRequest(BaseModel):
    epic: str
    signal: StrategySignal
    risk_plan: RiskPlan | None = None
    execution_mode: str = "paper"
    execution_provider: str = "paper"
    provider_deal_id: str | None = None
    provider_deal_reference: str | None = None
    execution_context: dict[str, Any] | None = None


class OpenLivePositionRequest(BaseModel):
    resolution: Resolution = "MINUTE_5"
    limit: int = Field(default=100, ge=5, le=500)
    manifest: StrategyManifest = Field(default_factory=StrategyManifest)


class ClosePositionRequest(BaseModel):
    close_price: float
    closed_at: str


class PositionListResponse(BaseModel):
    items: list[Position]


class PositionResponse(BaseModel):
    position: Position
