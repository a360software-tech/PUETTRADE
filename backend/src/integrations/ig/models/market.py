from pydantic import BaseModel


class MarketStatusSnapshot(BaseModel):
    epic: str
    market_status: str
    bid: float | None = None
    offer: float | None = None


class QuoteSnapshot(BaseModel):
    epic: str
    last_price: float | None = None
    bid: float | None = None
    offer: float | None = None
