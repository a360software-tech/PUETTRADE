from pydantic import BaseModel, Field

from strategy.domain.models import StrategySignal


class RiskSettings(BaseModel):
    account_balance: float = Field(gt=0)
    risk_per_trade_pct: float = Field(default=0.01, gt=0, le=0.05)
    stop_loss_pct: float = Field(default=0.0025, gt=0, le=0.05)
    take_profit_ratio: float = Field(default=2.0, gt=0.5, le=10.0)
    max_open_positions: int = Field(default=5, ge=1, le=100)
    max_position_notional_pct: float = Field(default=0.2, gt=0, le=1.0)


class RiskPlan(BaseModel):
    size: float
    capital_at_risk: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    notional_exposure: float


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    signal: StrategySignal | None = None
    plan: RiskPlan | None = None
