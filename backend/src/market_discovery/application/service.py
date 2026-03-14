from typing import Any

from shared.config.settings import Settings, get_settings
from shared.errors.base import AuthenticationError

from authentication.application.service import session_manager
from market_discovery.application.dto import (
    CategoryResponse,
    InstrumentResponse,
    MarketDetailResponse,
    MarketSearchResult,
)
from integrations.ig.rest.markets_client import IgMarketsClient


class MarketDiscoveryService:
    def __init__(self, settings: Settings) -> None:
        self._client = IgMarketsClient(settings)
        self._settings = settings

    def _get_auth_headers(self) -> dict[str, str]:
        session = session_manager.require_session()
        if not session.access_token:
            raise AuthenticationError()
        return {
            "Authorization": f"Bearer {session.access_token}",
            "X-IG-API-KEY": self._settings.ig_api_key,
        }

    async def get_categories(self) -> list[CategoryResponse]:
        auth_headers = self._get_auth_headers()
        data = await self._client.get_categories(auth_headers)

        categories: list[CategoryResponse] = []
        for cat in _as_list(data.get("categories")):
            categories.append(CategoryResponse(
                code=cat.get("code", ""),
                name=cat.get("name", cat.get("code", "")),
            ))
        return categories

    async def get_instruments(self, category_id: str) -> list[InstrumentResponse]:
        auth_headers = self._get_auth_headers()
        data = await self._client.get_instruments(category_id, auth_headers)

        instruments: list[InstrumentResponse] = []
        for inst in _as_list(data.get("instruments")):
            instruments.append(InstrumentResponse(
                epic=inst.get("epic", ""),
                instrument_name=inst.get("instrumentName", ""),
                expiry=inst.get("expiry"),
                instrument_type=inst.get("instrumentType", ""),
                lot_size=inst.get("lotSize"),
                otc_tradeable=inst.get("otcTradeable", False),
                market_status=inst.get("marketStatus", ""),
                bid=inst.get("bid"),
                offer=inst.get("offer"),
                high=inst.get("high"),
                low=inst.get("low"),
                net_change=inst.get("netChange"),
                percentage_change=inst.get("percentageChange"),
            ))
        return instruments

    async def search_markets(self, search_term: str) -> list[MarketSearchResult]:
        auth_headers = self._get_auth_headers()
        data = await self._client.search(search_term, auth_headers)

        results: list[MarketSearchResult] = []
        for market in _as_list(data.get("markets")):
            results.append(MarketSearchResult(
                epic=market.get("epic", ""),
                instrument_name=market.get("instrumentName", ""),
                instrument_type=market.get("instrumentType", ""),
                market_status=market.get("marketStatus", ""),
                bid=market.get("bid"),
                offer=market.get("offer"),
                high=market.get("high"),
                low=market.get("low"),
                net_change=market.get("netChange"),
                percentage_change=market.get("percentageChange"),
                streaming_prices_available=market.get("streamingPricesAvailable", False),
            ))
        return results

    async def get_market_detail(self, epic: str) -> MarketDetailResponse:
        auth_headers = self._get_auth_headers()
        data = await self._client.get_market(epic, auth_headers)

        market = _as_mapping(data.get("market"))

        return MarketDetailResponse(
            epic=market.get("epic", ""),
            instrument_name=market.get("instrumentName", ""),
            expiry=market.get("expiry"),
            instrument_type=market.get("instrumentType", ""),
            market_status=market.get("marketStatus", ""),
            bid=market.get("bid"),
            offer=market.get("offer"),
            high=market.get("high"),
            low=market.get("low"),
            net_change=market.get("netChange"),
            percentage_change=market.get("percentageChange"),
            scaling_factor=market.get("scalingFactor"),
            streaming_prices_available=market.get("streamingPricesAvailable", False),
            delay_time=market.get("delayTime"),
        )


def get_market_discovery_service() -> MarketDiscoveryService:
    return MarketDiscoveryService(get_settings())


def _as_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
