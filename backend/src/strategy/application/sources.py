from typing import Protocol

from market_data.application.dto import CandleItemResponse, Resolution
from market_data.domain.candles import BufferedCandle, stream_candle_buffer, to_lightstreamer_resolution
from market_data.infrastructure.candle_repository import CandleRepository, get_candle_repository


class StrategyCandleSource(Protocol):
    def get_candles(self, epic: str, resolution: Resolution, limit: int) -> list[CandleItemResponse]:
        ...


class StreamBufferStrategyCandleSource:
    def __init__(self, repository: CandleRepository | None = None) -> None:
        self._repository = repository or get_candle_repository()

    def get_candles(self, epic: str, resolution: Resolution, limit: int) -> list[CandleItemResponse]:
        buffered = stream_candle_buffer.get_series(
            epic=epic,
            resolution=to_lightstreamer_resolution(resolution),
            limit=limit,
            include_incomplete=False,
        )
        if len(buffered) >= limit:
            return [_to_candle_item(candle) for candle in buffered]

        persisted = self._repository.get_candles(epic, resolution, limit=limit)
        merged: dict[str, CandleItemResponse] = {candle.time: candle for candle in persisted}
        for candle in buffered:
            merged[candle.time] = _to_candle_item(candle)

        return [merged[key] for key in sorted(merged.keys())][-limit:]


def _to_candle_item(candle: BufferedCandle) -> CandleItemResponse:
    return CandleItemResponse(
        time=candle.time,
        open=candle.open_price,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )
