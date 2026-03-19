from pydantic import BaseModel, Field

from market_data.application.dto import CandleItemResponse, Resolution
from strategy.domain.models import IndicatorSnapshot, StrategyManifest, StrategySignal


class StrategyEvaluateRequest(BaseModel):
    epic: str
    resolution: Resolution = "MINUTE_5"
    candles: list[CandleItemResponse] = Field(min_length=5, max_length=1000)
    manifest: StrategyManifest = Field(default_factory=StrategyManifest)


class StrategyEvaluationResponse(BaseModel):
    epic: str
    resolution: Resolution
    manifest_name: str
    source: str = "manual"
    status: str = "ok"
    detail: str | None = None
    candles_analyzed: int
    latest_indicators: IndicatorSnapshot | None = None
    previous_indicators: IndicatorSnapshot | None = None
    signal: StrategySignal | None = None


class StrategyLiveQuery(BaseModel):
    resolution: Resolution = "MINUTE_5"
    limit: int = Field(default=100, ge=5, le=500)
    manifest: StrategyManifest = Field(default_factory=StrategyManifest)
