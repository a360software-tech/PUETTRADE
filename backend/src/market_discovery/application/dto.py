from pydantic import BaseModel
from typing import Optional


class CategoryResponse(BaseModel):
    code: str
    name: str


class WatchlistItemResponse(BaseModel):
    epic: str


class InstrumentResponse(BaseModel):
    epic: str
    instrument_name: str
    expiry: Optional[str] = None
    instrument_type: str
    lot_size: Optional[float] = None
    otc_tradeable: bool
    market_status: str
    bid: Optional[float] = None
    offer: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    net_change: Optional[float] = None
    percentage_change: Optional[float] = None


class MarketSearchResult(BaseModel):
    epic: str
    instrument_name: str
    instrument_type: str
    market_status: str
    bid: Optional[float] = None
    offer: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    net_change: Optional[float] = None
    percentage_change: Optional[float] = None
    streaming_prices_available: bool


class MarketDetailResponse(BaseModel):
    epic: str
    instrument_name: str
    expiry: Optional[str] = None
    instrument_type: str
    market_status: str
    bid: Optional[float] = None
    offer: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    net_change: Optional[float] = None
    percentage_change: Optional[float] = None
    scaling_factor: Optional[int] = None
    streaming_prices_available: bool
    delay_time: Optional[int] = None
