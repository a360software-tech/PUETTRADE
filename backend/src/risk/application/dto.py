from pydantic import BaseModel, Field

from market_data.application.dto import Resolution
from positions.domain.models import Position
from risk.domain.models import RiskDecision, RiskSettings
from strategy.domain.models import StrategyManifest, StrategySignal


class EvaluateRiskRequest(BaseModel):
    epic: str
    signal: StrategySignal
    settings: RiskSettings


class EvaluateLiveRiskRequest(BaseModel):
    resolution: Resolution = "MINUTE_5"
    limit: int = Field(default=100, ge=5, le=500)
    manifest: StrategyManifest = Field(default_factory=StrategyManifest)
    settings: RiskSettings


class RiskEvaluationResponse(BaseModel):
    epic: str
    decision: RiskDecision
    source: str


class RiskOpenPositionResponse(BaseModel):
    epic: str
    decision: RiskDecision
    position: Position
    source: str
