from time import monotonic

from shared.config.settings import Settings, get_settings

from authentication.application.service import AuthService
from integrations.ig.rest.prices_client import IgPricesClient
from integrations.ig.streaming.lightstreamer import CandleUpdate, lightstreamer_gateway
from market_data.application.dto import CandleItemResponse, CandlesResponse, CandleQuery, Resolution
from market_data.application.ports import HistoricalMarketDataPort, StreamingMarketDataPort
from market_data.domain.candles import BufferedCandle, stream_candle_buffer, supports_buffered_resolution, to_lightstreamer_resolution
from market_data.infrastructure.candle_repository import CandleRepository, get_candle_repository, reseed_buffer_from_persistence
from shared.errors.base import IntegrationError

_CACHE_TTL_SECONDS = 10.0
_candle_cache: dict[tuple[str, str, int, str | None, str | None, str], tuple[float, CandlesResponse]] = {}


class MarketDataService(HistoricalMarketDataPort):
    def __init__(self, settings: Settings, repository: CandleRepository | None = None) -> None:
        self._settings = settings
        self._client = IgPricesClient(settings)
        self._repository = repository or get_candle_repository()

    async def get_candles(
        self,
        epic: str,
        query: CandleQuery,
        access_token: str | None,
        auth_service: AuthService,
    ) -> CandlesResponse:
        cache_key = (epic, query.resolution, query.max, query.from_, query.to, access_token)
        cached = _candle_cache.get(cache_key)
        if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1].model_copy(deep=True)

        persisted = reseed_buffer_from_persistence(self._repository, epic, query.resolution, query.max)
        if persisted and (len(persisted) >= query.max or not access_token):
            response = CandlesResponse(
                epic=epic,
                resolution=query.resolution,
                candles=persisted[-query.max:],
                allowance_remaining=None,
                allowance_total=None,
            )
            _candle_cache[cache_key] = (monotonic(), response.model_copy(deep=True))
            return response

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
            candles=[_map_price_to_candle_item(epic, price) for price in prices],
            allowance_remaining=_as_int(allowance.get("remainingAllowance")),
            allowance_total=_as_int(allowance.get("totalAllowance")),
        )
        self._repository.upsert_many(epic, query.resolution, response.candles, source="rest")
        _seed_stream_buffer_from_history(epic=epic, resolution=query.resolution, candles=response.candles)
        _candle_cache[cache_key] = (monotonic(), response.model_copy(deep=True))
        return response


def get_market_data_service() -> MarketDataService:
    return MarketDataService(get_settings())


def _map_price_to_candle_item(epic: str, price: dict[str, object]) -> CandleItemResponse:
    open_price = _as_dict(price.get("openPrice"))
    high_price = _as_dict(price.get("highPrice"))
    low_price = _as_dict(price.get("lowPrice"))
    close_price = _as_dict(price.get("closePrice"))

    return CandleItemResponse(
        time=str(price.get("snapshotTimeUTC") or price.get("snapshotTime") or ""),
        open=_normalize_historical_price(epic, _pick_price(open_price)),
        high=_normalize_historical_price(epic, _pick_price(high_price)),
        low=_normalize_historical_price(epic, _pick_price(low_price)),
        close=_normalize_historical_price(epic, _pick_price(close_price)),
        volume=_as_float(price.get("lastTradedVolume")),
    )


def _normalize_historical_price(epic: str, value: float) -> float:
    if value == 0.0:
        return value
        
    code = epic.split(".")[2] if len(epic.split(".")) > 2 else epic
    if len(code) == 6 and code.isalpha():
        # If the value is already normal (e.g. 1.33642), don't alter it
        if value < 100.0 and code[3:] != "JPY":
            return value
        if value < 1000.0 and code[3:] == "JPY":
            return value

        quote = code[3:]
        if quote == "JPY":
            if value >= 1000.0:
                return value / 100.0
        else:
            if value >= 100.0:
                return value / 10000.0
                
    return value


def _pick_price(price: dict[str, object]) -> float:
    for key in ("bid", "ask", "lastTraded"):
        value = _as_float(price.get(key))
        if value is not None:
            return value
    return 0.0


def _build_stream_fallback(epic: str, resolution: Resolution, max_points: int) -> CandlesResponse | None:
    buffered = _streaming_port().get_buffered_candles(
        epic=epic,
        resolution=to_lightstreamer_resolution(resolution),
        limit=max_points,
    )
    buffered = [candle for candle in buffered if _is_plausible_stream_candle(epic, candle)]
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
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
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


def _is_plausible_stream_candle(epic: str, candle: CandleUpdate) -> bool:
    code = epic.split(".")[2] if len(epic.split(".")) > 2 else epic
    close = candle.close
    if len(code) == 6 and code.isalpha():
        quote = code[3:]
        if quote == "JPY":
            return 10.0 <= close <= 1000.0
        return 0.1 <= close <= 10.0

    if "GOLD" in code or code == "XAUUSD":
        return 100.0 <= close <= 10000.0

    if code in {"DAX", "GER40", "DE40"} or epic.startswith("IX."):
        return 1000.0 <= close <= 100000.0

    return close > 0.0


def _seed_stream_buffer_from_history(epic: str, resolution: Resolution, candles: list[CandleItemResponse]) -> None:
    if not candles or not supports_buffered_resolution(resolution):
        return

    buffered_resolution = to_lightstreamer_resolution(resolution)
    stream_candle_buffer.seed_completed(
        BufferedCandle(
            epic=epic,
            resolution=buffered_resolution,
            time=candle.time,
            open_price=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=0.0 if candle.volume is None else candle.volume,
            completed=True,
        )
        for candle in candles
    )


def _streaming_port() -> StreamingMarketDataPort:
    return lightstreamer_gateway
