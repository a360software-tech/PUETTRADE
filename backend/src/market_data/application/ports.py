from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from authentication.application.dto import StreamingTokensResponse
from market_data.application.dto import CandleQuery, CandlesResponse
from market_data.domain.candles import BufferedCandle


@dataclass(slots=True)
class MarketTick:
    epic: str
    price: float
    timestamp: str | float
    volume: float = 0.0


class HistoricalMarketDataPort(Protocol):
    async def get_candles(
        self,
        epic: str,
        query: CandleQuery,
        access_token: str | None,
        auth_service,
    ) -> CandlesResponse:
        ...


class StreamingMarketDataPort(Protocol):
    @property
    def is_connected(self) -> bool:
        ...

    async def connect(self, credentials) -> None:
        ...

    async def disconnect(self) -> None:
        ...

    async def subscribe_to_candles(
        self,
        epic: str,
        resolution: str,
        callback: Callable,
    ) -> str:
        ...

    async def unsubscribe(self, epic: str, resolution: str, listener_id: str) -> None:
        ...

    def get_buffered_candles(self, epic: str, resolution: str, limit: int = 200) -> list:
        ...


class BrokerSessionPort(Protocol):
    async def get_session_tokens(self) -> StreamingTokensResponse:
        ...

    def get_access_token(self) -> str:
        ...
