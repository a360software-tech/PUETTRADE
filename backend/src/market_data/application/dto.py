from typing import Literal

from pydantic import BaseModel, Field

Resolution = Literal[
    "SECOND",
    "MINUTE",
    "MINUTE_2",
    "MINUTE_3",
    "MINUTE_5",
    "MINUTE_10",
    "MINUTE_15",
    "MINUTE_30",
    "HOUR",
    "HOUR_2",
    "HOUR_3",
    "HOUR_4",
    "DAY",
    "WEEK",
    "MONTH",
]


class CandleItemResponse(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class CandlesResponse(BaseModel):
    epic: str
    resolution: Resolution
    candles: list[CandleItemResponse]
    allowance_remaining: int | None = None
    allowance_total: int | None = None


class CandleQuery(BaseModel):
    resolution: Resolution = "MINUTE"
    max: int = Field(default=200, ge=1, le=1000)
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
