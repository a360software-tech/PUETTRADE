from typing import Protocol

from market_data.application.dto import CandleItemResponse, Resolution
from market_data.domain.candles import BufferedCandle, stream_candle_buffer, to_lightstreamer_resolution


class StrategyCandleSource(Protocol):
    def get_candles(self, epic: str, resolution: Resolution, limit: int) -> list[CandleItemResponse]:
        ...


class StreamBufferStrategyCandleSource:
    def get_candles(self, epic: str, resolution: Resolution, limit: int) -> list[CandleItemResponse]:
        buffered = stream_candle_buffer.get(
            epic=epic,
            resolution=to_lightstreamer_resolution(resolution),
            limit=limit,
        )
        completed = [candle for candle in buffered if candle.completed]
        return [_to_candle_item(candle) for candle in completed]


def _to_candle_item(candle: BufferedCandle) -> CandleItemResponse:
    return CandleItemResponse(
        time=candle.time,
        open=candle.open_price,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )
