from time import monotonic

from shared.config.settings import Settings, get_settings

from authentication.application.service import AuthService
from integrations.ig.rest.prices_client import IgPricesClient
from integrations.ig.streaming.lightstreamer import lightstreamer_gateway
from market_data.application.dto import CandleItemResponse, CandlesResponse, CandleQuery
from shared.errors.base import IntegrationError

_CACHE_TTL_SECONDS = 10.0
_candle_cache: dict[tuple[str, str, int, str | None, str | None, str], tuple[float, CandlesResponse]] = {}


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

        cache_key = (epic, query.resolution, query.max, query.from_, query.to, access_token)
        cached = _candle_cache.get(cache_key)
        if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1].model_copy(deep=True)

        tokens = await auth_service.get_session_tokens()
        
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-IG-API-KEY": self._settings.ig_api_key,
            "CST": tokens.cst,
            "X-SECURITY-TOKEN": tokens.x_security_token,
            "IG-ACCOUNT-ID": tokens.account_id,
        }
        
        try:
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
        except IntegrationError as exc:
            fallback = _build_stream_fallback(epic=epic, resolution=query.resolution, max_points=query.max)
            if fallback is not None and _is_historical_allowance_error(exc):
                return fallback
            raise

        prices = _as_list_of_dicts(payload.get("prices"))
        allowance = _as_dict(payload.get("allowance"))

        response = CandlesResponse(
            epic=epic,
            resolution=query.resolution,
            candles=[_map_price_to_candle_item(price) for price in prices],
            allowance_remaining=_as_int(allowance.get("remainingAllowance")),
            allowance_total=_as_int(allowance.get("totalAllowance")),
        )
        _candle_cache[cache_key] = (monotonic(), response.model_copy(deep=True))
        return response


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


def _build_stream_fallback(epic: str, resolution: str, max_points: int) -> CandlesResponse | None:
    resolution_map = {
        "MINUTE": "1MINUTE",
        "MINUTE_2": "2MINUTE",
        "MINUTE_3": "3MINUTE",
        "MINUTE_5": "5MINUTE",
        "MINUTE_10": "10MINUTE",
        "MINUTE_15": "15MINUTE",
        "MINUTE_30": "30MINUTE",
        "HOUR": "1HOUR",
        "HOUR_2": "2HOUR",
        "HOUR_3": "3HOUR",
        "HOUR_4": "4HOUR",
        "DAY": "1DAY",
    }

    buffered = lightstreamer_gateway.get_buffered_candles(
        epic=epic,
        resolution=resolution_map.get(resolution, "1MINUTE"),
        limit=max_points,
    )
    if not buffered:
        return None

    return CandlesResponse(
        epic=epic,
        resolution=resolution,
        candles=[
            CandleItemResponse(
                time=candle.time,
                open=candle.open_price,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
            for candle in buffered
        ],
        allowance_remaining=None,
        allowance_total=None,
    )


def _is_historical_allowance_error(error: IntegrationError) -> bool:
    return "error.public-api.exceeded-account-historical-data-allowance" in error.detail


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
