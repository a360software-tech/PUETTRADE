from datetime import datetime
from decimal import Decimal

from shared.domain.models import Candle


def map_ig_price_to_candle(epic: str, resolution: str, payload: dict[str, object]) -> Candle:
    open_price = payload.get("openPrice", {}) or {}
    high_price = payload.get("highPrice", {}) or {}
    low_price = payload.get("lowPrice", {}) or {}
    close_price = payload.get("closePrice", {}) or {}

    return Candle(
        epic=epic,
        resolution=resolution,
        timestamp=datetime.fromisoformat(str(payload.get("snapshotTimeUTC", "1970-01-01T00:00:00"))),
        open_bid=_decimal_or_none(open_price.get("bid")),
        high_bid=_decimal_or_none(high_price.get("bid")),
        low_bid=_decimal_or_none(low_price.get("bid")),
        close_bid=_decimal_or_none(close_price.get("bid")),
        open_ask=_decimal_or_none(open_price.get("ask")),
        high_ask=_decimal_or_none(high_price.get("ask")),
        low_ask=_decimal_or_none(low_price.get("ask")),
        close_ask=_decimal_or_none(close_price.get("ask")),
        last_traded_volume=_decimal_or_none(payload.get("lastTradedVolume")),
    )


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
