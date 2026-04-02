from shared.config.settings import Settings, get_settings

from authentication.application.service import AuthService
from market_data.application.dto import CandleQuery, CandlesResponse
from market_data.application.history_service import MarketHistoryService
from market_data.application.ports import HistoricalMarketDataPort
from market_data.infrastructure.candle_repository import CandleRepository, get_candle_repository


class MarketDataService(HistoricalMarketDataPort):
    def __init__(self, settings: Settings, repository: CandleRepository | None = None) -> None:
        self._repository = repository or get_candle_repository()
        self._history = MarketHistoryService(settings, self._repository)

    async def get_candles(
        self,
        epic: str,
        query: CandleQuery,
        access_token: str | None,
        auth_service: AuthService,
    ) -> CandlesResponse:
        return await self._history.get_candles(epic, query, access_token, auth_service)


def get_market_data_service() -> MarketDataService:
    return MarketDataService(get_settings())
