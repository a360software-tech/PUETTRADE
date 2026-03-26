import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4
from typing import Callable, Optional

from lightstreamer_client import LightstreamerClient, LightstreamerSubscription
from integrations.ig.rest.markets_client import IgMarketsClient
from market_data.domain.candles import (
    BufferedCandle,
    TickCandleBuilder,
    TickInput,
    candle_close_notifier,
    stream_candle_buffer,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LightstreamerCredentials:
    account_id: str
    access_token: str
    cst: str
    x_security_token: str
    endpoint: str


@dataclass(slots=True)
class TickUpdate:
    epic: str
    bid: float | None
    offer: float | None
    price: float
    time: str


@dataclass(slots=True)
class CandleUpdate:
    epic: str
    time: str
    open_price: float
    high: float
    low: float
    close: float
    volume: float
    completed: bool


class LightstreamerGateway:
    def __init__(self) -> None:
        self._client: Optional[LightstreamerClient] = None
        self._credentials: Optional[LightstreamerCredentials] = None
        self._candle_listeners: dict[str, dict[str, Callable[[CandleUpdate], None]]] = {}
        self._candle_tick_links: dict[str, dict[str, str]] = {}
        self._tick_subscriptions: dict[str, str] = {}
        self._tick_subscription_modes: dict[str, str] = {}
        self._tick_listeners: dict[str, dict[str, Callable[[TickUpdate], None]]] = {}
        self._latest_ticks: dict[str, TickUpdate] = {}
        self._market_metadata: dict[str, dict[str, float | int | None]] = {}
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, credentials: LightstreamerCredentials) -> None:
        async with self._lock:
            if self._connected and self._credentials:
                return

            self._credentials = credentials
            endpoint = credentials.endpoint or "https://demo-apd.marketdatasystems.com"
            password = f"CST-{credentials.cst}|XST-{credentials.x_security_token}"

            self._client = LightstreamerClient(credentials.account_id, password, endpoint)
            client = self._client
            if client is None:
                raise RuntimeError("Lightstreamer client unavailable")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.connect)
            await asyncio.sleep(2)
            self._connected = True
            logger.info("Connected to Lightstreamer: %s", endpoint)

    async def disconnect(self) -> None:
        async with self._lock:
            for sub_key in list(self._tick_subscriptions.values()):
                if sub_key and self._client:
                    try:
                        self._client.unsubscribe(sub_key)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Error unsubscribing: %s", exc)

            self._tick_subscriptions.clear()
            self._tick_subscription_modes.clear()
            self._tick_listeners.clear()
            self._candle_listeners.clear()
            self._candle_tick_links.clear()
            self._latest_ticks.clear()
            self._market_metadata.clear()
            stream_candle_buffer.clear()

            if self._client:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._client.disconnect)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Error disconnecting: %s", exc)

            self._connected = False
            self._client = None

    async def subscribe_to_candles(
        self,
        epic: str,
        resolution: str = "1MINUTE",
        callback: Callable[[CandleUpdate], None] | None = None,
    ) -> str:
        if callback is None:
            raise ValueError("callback is required")

        candle_key = f"{epic}:{resolution}"
        listener_id = str(uuid4())
        self._candle_listeners.setdefault(candle_key, {})[listener_id] = callback
        self._candle_tick_links.setdefault(candle_key, {})

        builder = TickCandleBuilder(buffer=stream_candle_buffer, notifier=candle_close_notifier, resolutions=[resolution])

        def on_tick(update: TickUpdate) -> None:
            tick_input = TickInput(epic=update.epic, price=update.price, timestamp=update.time, volume=0.0)
            closed = builder.update_with_tick(tick_input)
            for candle in closed:
                _dispatch_candle_update(self._candle_listeners, candle_key, _to_candle_update(candle, completed=True))

            current = stream_candle_buffer.get_current(epic=epic, resolution=resolution)
            if current is not None:
                _dispatch_candle_update(self._candle_listeners, candle_key, _to_candle_update(current, completed=False))

        tick_listener_id = await self.subscribe_to_ticks(epic, on_tick)
        self._candle_tick_links[candle_key][listener_id] = tick_listener_id
        logger.info("Subscribed candle stream via tick feed epic=%s resolution=%s", epic, resolution)
        return listener_id

    async def subscribe_to_ticks(self, epic: str, callback: Callable[[TickUpdate], None]) -> str:
        if not self._client or not self._connected:
            raise RuntimeError("Not connected to Lightstreamer")

        listener_id = str(uuid4())
        listeners = self._tick_listeners.setdefault(epic, {})
        listeners[listener_id] = callback

        if epic in self._tick_subscriptions:
            return listener_id

        await self._ensure_market_metadata(epic)

        sub_key, mode = await self._subscribe_tick_stream(epic)
        self._tick_subscriptions[epic] = sub_key
        self._tick_subscription_modes[epic] = mode
        logger.info("Subscribed tick stream epic=%s mode=%s", epic, mode)
        return listener_id

    async def unsubscribe(self, epic: str, resolution: str, listener_id: str) -> None:
        candle_key = f"{epic}:{resolution}"
        listeners = self._candle_listeners.get(candle_key)
        if listeners is not None:
            listeners.pop(listener_id, None)

        tick_links = self._candle_tick_links.get(candle_key)
        tick_listener_id = None if tick_links is None else tick_links.pop(listener_id, None)
        if tick_listener_id is not None:
            await self.unsubscribe_ticks(epic, tick_listener_id)

        if listeners:
            return

        self._candle_listeners.pop(candle_key, None)
        self._candle_tick_links.pop(candle_key, None)

    async def unsubscribe_ticks(self, epic: str, listener_id: str) -> None:
        listeners = self._tick_listeners.get(epic)
        if listeners is not None:
            listeners.pop(listener_id, None)

        if listeners:
            return

        sub_key = self._tick_subscriptions.get(epic)
        if sub_key and self._client:
            try:
                client = self._client
                if client is None:
                    return
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, client.unsubscribe, sub_key)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error unsubscribing tick stream for %s: %s", epic, exc)

        self._tick_subscriptions.pop(epic, None)
        self._tick_subscription_modes.pop(epic, None)
        self._tick_listeners.pop(epic, None)
        self._latest_ticks.pop(epic, None)

    def get_latest_tick(self, epic: str) -> TickUpdate | None:
        return self._latest_ticks.get(epic)

    def get_latest_price(self, epic: str) -> float | None:
        tick = self.get_latest_tick(epic)
        return None if tick is None else tick.price

    def get_buffered_candles(self, epic: str, resolution: str, limit: int = 200) -> list[CandleUpdate]:
        candles = stream_candle_buffer.get(epic=epic, resolution=resolution, limit=limit)
        return [_to_candle_update(candle, completed=candle.completed) for candle in candles]

    async def _subscribe_tick_stream(self, epic: str) -> tuple[str, str]:
        try:
            return await self._subscribe_tick_stream_mode(epic, mode="MARKET")
        except Exception as exc:  # noqa: BLE001
            logger.warning("MARKET stream failed for %s, falling back to PRICE: %s", epic, exc)
            return await self._subscribe_tick_stream_mode(epic, mode="PRICE")

    async def _subscribe_tick_stream_mode(self, epic: str, *, mode: str) -> tuple[str, str]:
        client = self._client
        credentials = self._credentials
        if client is None or credentials is None:
            raise RuntimeError("Lightstreamer client unavailable")

        item_name = f"MARKET:{epic}" if mode == "MARKET" else f"PRICE:{credentials.account_id}:{epic}"
        fields = ["BID", "OFFER", "UPDATE_TIME"]

        def on_item_update(update) -> None:
            try:
                item = str(update.get("name") or "")
                if item and item != item_name:
                    logger.warning(
                        "Lightstreamer item mismatch for %s: expected=%s received=%s",
                        epic,
                        item_name,
                        item,
                    )
                    return

                values = update.get("values")
                if not isinstance(values, dict):
                    logger.debug("Lightstreamer tick update missing values epic=%s update=%s", epic, update)
                    return

                bid = _as_optional_float(values.get("BID"))
                offer = _as_optional_float(values.get("OFFER"))
                if bid is None and offer is None:
                    return

                scaling_factor = self._get_scaling_factor(epic)
                bid = _normalize_scaled_price(epic, bid, scaling_factor)
                offer = _normalize_scaled_price(epic, offer, scaling_factor)

                price = _mid_price(bid, offer)
                logger.debug("TICK_DEBUG epic=%s raw_bid=%s raw_offer=%s normalized_mid=%s scaling_factor=%s", epic, values.get("BID"), values.get("OFFER"), price, scaling_factor)
                if price is None or not _is_plausible_price(epic, price):
                    logger.warning(
                        "Discarded implausible tick update epic=%s mode=%s item=%s price=%s",
                        epic,
                        mode,
                        item or item_name,
                        price,
                    )
                    return

                update_time = _normalize_tick_time(values.get("UPDATE_TIME"))
                tick = TickUpdate(epic=epic, bid=bid, offer=offer, price=price, time=update_time)
                self._latest_ticks[epic] = tick
                for listener in list(self._tick_listeners.get(epic, {}).values()):
                    try:
                        listener(tick)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Error dispatching tick update: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error processing tick update: %s", exc)

        subscription = LightstreamerSubscription(mode="MERGE", items=[item_name], fields=fields)
        subscription.addlistener(on_item_update)

        loop = asyncio.get_event_loop()
        raw_sub_key: object | None = await loop.run_in_executor(None, client.subscribe, subscription)
        sub_key = None if raw_sub_key is None else str(raw_sub_key)
        if not sub_key:
            raise RuntimeError(f"Failed to subscribe to {item_name}")
        return sub_key, mode

    async def _ensure_market_metadata(self, epic: str) -> None:
        if epic in self._market_metadata:
            return

        credentials = self._credentials
        if credentials is None:
            self._market_metadata[epic] = {"scaling_factor": None}
            return

        try:
            client = IgMarketsClient(_build_settings_for_stream(credentials.endpoint))
            data = await client.get_market(
                epic,
                {
                    "Authorization": f"Bearer {credentials.access_token}",
                    "CST": credentials.cst,
                    "X-SECURITY-TOKEN": credentials.x_security_token,
                    "IG-ACCOUNT-ID": credentials.account_id,
                },
            )
            snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
            scaling_factor = _as_optional_int(snapshot.get("scalingFactor"))
            self._market_metadata[epic] = {"scaling_factor": scaling_factor}
            logger.info("Loaded market metadata epic=%s scaling_factor=%s", epic, scaling_factor)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load market metadata for %s: %s", epic, exc)
            self._market_metadata[epic] = {"scaling_factor": None}

    def _get_scaling_factor(self, epic: str) -> int | None:
        metadata = self._market_metadata.get(epic)
        if not metadata:
            return None
        raw = metadata.get("scaling_factor")
        return raw if isinstance(raw, int) else None


lightstreamer_gateway = LightstreamerGateway()


def _dispatch_candle_update(
    listeners_by_key: dict[str, dict[str, Callable[[CandleUpdate], None]]],
    candle_key: str,
    update: CandleUpdate,
) -> None:
    for listener in list(listeners_by_key.get(candle_key, {}).values()):
        try:
            listener(update)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error dispatching candle update: %s", exc)


def _to_candle_update(candle: BufferedCandle, *, completed: bool) -> CandleUpdate:
    return CandleUpdate(
        epic=candle.epic,
        time=candle.time,
        open_price=candle.open_price,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        completed=completed,
    )


def _as_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _mid_price(bid: float | None, offer: float | None) -> float | None:
    if bid is not None and offer is not None:
        return (bid + offer) / 2
    return bid if bid is not None else offer


def _normalize_tick_time(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _normalize_scaled_price(epic: str, value: float | None, scaling_factor: int | None) -> float | None:
    if value is None:
        return None
    
    # Heuristic for Forex pairs to override broken scaling factors from snapshot
    code = epic.split(".")[2] if len(epic.split(".")) > 2 else epic
    if len(code) == 6 and code.isalpha():
        # If the value is already normal (e.g. 1.33642), don't alter it
        if value < 100.0 and code[3:] != "JPY":
            return value
        if value < 1000.0 and code[3:] == "JPY":
            return value

        quote = code[3:]
        if quote == "JPY":
            if value > 1000.0:
                return value / 100.0
        else:
            if value > 100.0:
                return value / 10000.0

    if scaling_factor is None or scaling_factor <= 1:
        return value
        
    if scaling_factor >= 10:
        return value / scaling_factor
        
    return value / (10 ** scaling_factor)


def _build_settings_for_stream(endpoint: str):
    from shared.config.settings import get_settings

    settings = get_settings().model_copy(deep=True)
    settings.ig_lightstreamer_url = endpoint or settings.ig_lightstreamer_url
    return settings


def _is_plausible_price(epic: str, price: float) -> bool:
    code = epic.split(".")[2] if len(epic.split(".")) > 2 else epic
    if len(code) == 6 and code.isalpha():
        quote = code[3:]
        if quote == "JPY":
            return 10.0 <= price <= 1000.0
        return 0.1 <= price <= 10.0

    if "GOLD" in code or code == "XAUUSD":
        return 100.0 <= price <= 10000.0

    if code in {"DAX", "GER40", "DE40"} or epic.startswith("IX."):
        return 1000.0 <= price <= 100000.0

    return price > 0.0
