from shared.config.settings import Settings, get_settings

from authentication.application.service import AuthService
from integrations.ig.rest.prices_client import IgPricesClient
from market_data.application.dto import CandleItemResponse, CandlesResponse, CandleQuery


class MarketDataService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = IgPricesClient(settings)

    async def get_candles(
        self,
        epic: str,
        query: CandleQuery,
        access_token: str | None,
        auth_service: AuthService,
    ) -> CandlesResponse:
        if not access_token:
            from shared.errors.base import NotAuthenticatedError
            raise NotAuthenticatedError("No access token provided")

        tokens = await auth_service.get_session_tokens()
        
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-IG-API-KEY": self._settings.ig_api_key,
            "CST": tokens.cst,
            "X-SECURITY-TOKEN": tokens.x_security_token,
            "IG-ACCOUNT-ID": tokens.account_id,
        }
        
        if query.from_ and query.to:
            payload = await self._client.get_prices_by_range(
                epic=epic,
                resolution=query.resolution,
                start_date=query.from_,
                end_date=query.to,
                auth_headers=auth_headers,
            )
        else:
            payload = await self._client.get_prices(
                epic=epic,
                resolution=query.resolution,
                auth_headers=auth_headers,
                max_points=query.max,
            )

        prices = _as_list_of_dicts(payload.get("prices"))
        allowance = _as_dict(payload.get("allowance"))

        return CandlesResponse(
            epic=epic,
            resolution=query.resolution,
            candles=[_map_price_to_candle_item(price) for price in prices],
            allowance_remaining=_as_int(allowance.get("remainingAllowance")),
            allowance_total=_as_int(allowance.get("totalAllowance")),
        )


def get_market_data_service() -> MarketDataService:
    return MarketDataService(get_settings())


def _map_price_to_candle_item(price: dict[str, object]) -> CandleItemResponse:
    open_price = _as_dict(price.get("openPrice"))
    high_price = _as_dict(price.get("highPrice"))
    low_price = _as_dict(price.get("lowPrice"))
    close_price = _as_dict(price.get("closePrice"))

    return CandleItemResponse(
        time=str(price.get("snapshotTimeUTC") or price.get("snapshotTime") or ""),
        open=_pick_price(open_price),
        high=_pick_price(high_price),
        low=_pick_price(low_price),
        close=_pick_price(close_price),
        volume=_as_float(price.get("lastTradedVolume")),
    )


def _pick_price(price: dict[str, object]) -> float:
    for key in ("bid", "ask", "lastTraded"):
        value = _as_float(price.get(key))
        if value is not None:
            return value
    return 0.0


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
