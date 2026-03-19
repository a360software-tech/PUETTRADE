from enum import Enum

from pydantic import BaseModel, Field


class SignalSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class IndicatorConfig(BaseModel):
    rsi_period: int = Field(default=14, ge=2, le=100)
    fast_ema: int = Field(default=9, ge=2, le=200)
    slow_ema: int = Field(default=21, ge=2, le=400)


class TriggerRule(BaseModel):
    condition: str
    action: SignalSide


class StrategyManifest(BaseModel):
    name: str = "Genesis"
    indicators: IndicatorConfig = Field(default_factory=IndicatorConfig)
    triggers: list[TriggerRule] = Field(
        default_factory=lambda: [
            TriggerRule(condition="EMA_CROSS_UP", action=SignalSide.LONG),
            TriggerRule(condition="EMA_CROSS_DOWN", action=SignalSide.SHORT),
            TriggerRule(condition="RSI < 30", action=SignalSide.LONG),
            TriggerRule(condition="RSI > 70", action=SignalSide.SHORT),
        ]
    )


class StrategySignal(BaseModel):
    side: SignalSide
    price: float
    time: str
    momentum: float | None = None
    phase: str | None = None
    reason: str


class IndicatorSnapshot(BaseModel):
    close: float
    fast_ema: float | None = None
    slow_ema: float | None = None
    rsi: float | None = None
