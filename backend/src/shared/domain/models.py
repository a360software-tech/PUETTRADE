from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class Epic:
    value: str


@dataclass(slots=True)
class Candle:
    epic: str
    resolution: str
    timestamp: datetime
    open_bid: Decimal | None = None
    high_bid: Decimal | None = None
    low_bid: Decimal | None = None
    close_bid: Decimal | None = None
    open_ask: Decimal | None = None
    high_ask: Decimal | None = None
    low_ask: Decimal | None = None
    close_ask: Decimal | None = None
    last_traded_volume: Decimal | None = None


@dataclass(slots=True)
class PositionSnapshot:
    deal_id: str
    epic: str
    direction: str
    size: Decimal
    level: Decimal


@dataclass(slots=True)
class AccountSnapshot:
    account_id: str
    balance: Decimal
    available: Decimal
    profit_loss: Decimal
