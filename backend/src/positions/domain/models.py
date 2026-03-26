from enum import Enum
from typing import Any

from pydantic import BaseModel

from strategy.domain.models import StrategySignal


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Position(BaseModel):
    id: str
    epic: str
    side: str
    entry_price: float
    size: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    execution_mode: str = "paper"
    execution_provider: str = "paper"
    provider_deal_id: str | None = None
    provider_deal_reference: str | None = None
    execution_context: dict[str, Any] | None = None
    opened_at: str
    status: PositionStatus
    signal: StrategySignal
    close_price: float | None = None
    closed_at: str | None = None
    pnl_points: float | None = None
