import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
from typing import Callable, Optional

from lightstreamer_client import LightstreamerClient, LightstreamerSubscription
from market_data.domain.candles import BufferedCandle, candle_close_notifier, stream_candle_buffer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LightstreamerCredentials:
    account_id: str
    cst: str
    x_security_token: str
    endpoint: str


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
        self._subscriptions: dict[str, str] = {}
        self._listeners: dict[str, dict[str, Callable[[CandleUpdate], None]]] = {}
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
            endpoint = credentials.endpoint

            if not endpoint:
                endpoint = "https://demo-apd.marketdatasystems.com"

            password = f"CST-{credentials.cst}|XST-{credentials.x_security_token}"

            self._client = LightstreamerClient(
                credentials.account_id,
                password,
                endpoint
            )
            client = self._client
            if client is None:
                raise RuntimeError("Lightstreamer client unavailable")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.connect)

            await asyncio.sleep(2)
            self._connected = True
            logger.info(f"Connected to Lightstreamer: {endpoint}")

    async def disconnect(self) -> None:
        async with self._lock:
            for sub_key in list(self._subscriptions.values()):
                if sub_key and self._client:
                    try:
                        self._client.unsubscribe(sub_key)
                    except Exception as e:
                        logger.error(f"Error unsubscribing: {e}")

            self._subscriptions.clear()
            self._listeners.clear()
            stream_candle_buffer.clear()

            if self._client:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._client.disconnect)
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")

            self._connected = False
            self._client = None

    async def subscribe_to_candles(
        self,
        epic: str,
        resolution: str = "1MINUTE",
        callback: Callable[[CandleUpdate], None] | None = None,
    ) -> str:
        if not callback:
            raise ValueError("callback is required")

        if not self._client or not self._connected:
            raise RuntimeError("Not connected to Lightstreamer")

        client = self._client
        if client is None:
            raise RuntimeError("Lightstreamer client unavailable")

        subscription_key = f"{epic}:{resolution}"
        listener_id = str(uuid4())
        listeners = self._listeners.setdefault(subscription_key, {})
        listeners[listener_id] = callback

        sub_key = self._subscriptions.get(subscription_key)
        if sub_key:
            return listener_id

        item_name = f"CHART:{epic}:{resolution}"
        fields = ["BID_OPEN", "BID_HIGH", "BID_LOW", "BID_CLOSE", "CONS_END", "UTM", "LTV"]

        def emit(update: CandleUpdate) -> None:
            stream_candle_buffer.upsert(
                BufferedCandle(
                    epic=update.epic,
                    resolution=resolution,
                    time=update.time,
                    open_price=update.open_price,
                    high=update.high,
                    low=update.low,
                    close=update.close,
                    volume=update.volume,
                    completed=update.completed,
                )
            )
            if update.completed:
                candle_close_notifier.notify(
                    BufferedCandle(
                        epic=update.epic,
                        resolution=resolution,
                        time=update.time,
                        open_price=update.open_price,
                        high=update.high,
                        low=update.low,
                        close=update.close,
                        volume=update.volume,
                        completed=True,
                    )
                )

            for listener in list(self._listeners.get(subscription_key, {}).values()):
                try:
                    listener(update)
                except Exception as e:
                    logger.error(f"Error dispatching candle update: {e}")

        def build_candle_update(candle: BufferedCandle, completed: bool) -> CandleUpdate:
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

        def on_item_update(update) -> None:
            try:
                item_name = str(update.get("name") or "")
                if item_name and item_name != item_name_expected:
                    logger.warning(
                        "Lightstreamer item mismatch for %s: expected=%s received=%s",
                        subscription_key,
                        item_name_expected,
                        item_name,
                    )
                    return

                values = update.get("values")
                if not isinstance(values, dict):
                    logger.debug("Lightstreamer update missing values for %s: %s", subscription_key, update)
                    return

                bid_open = values.get("BID_OPEN")
                bid_high = values.get("BID_HIGH")
                bid_low = values.get("BID_LOW")
                bid_close = values.get("BID_CLOSE")
                cons_end = values.get("CONS_END")
                utm = values.get("UTM")
                ltv = values.get("LTV")

                if not bid_close:
                    return

                completed = cons_end == "1" if cons_end else False
                close = float(bid_close)
                if not _is_plausible_price(epic, close):
                    logger.warning(
                        "Discarded implausible candle update epic=%s resolution=%s item=%s close=%s",
                        epic,
                        resolution,
                        item_name or item_name_expected,
                        close,
                    )
                    return

                timestamp_ms = int(utm) if utm else int(datetime.now().timestamp() * 1000)
                candle_time = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%dT%H:%M:%S")
                current = stream_candle_buffer.get_current(epic=epic, resolution=resolution)

                if completed and current is not None:
                    emit(build_candle_update(current, completed=True))
                    current = None

                if current is None:
                    high = float(bid_high) if bid_high else close
                    low = float(bid_low) if bid_low else close
                    current = BufferedCandle(
                        epic=epic,
                        resolution=resolution,
                        time=candle_time,
                        open_price=float(bid_open) if bid_open else close,
                        high=high,
                        low=low,
                        close=close,
                        volume=float(ltv) if ltv else 0.0,
                        completed=False,
                    )
                else:
                    high = float(bid_high) if bid_high else close
                    low = float(bid_low) if bid_low else close
                    current = BufferedCandle(
                        epic=epic,
                        resolution=resolution,
                        time=current.time if current.time == candle_time else candle_time,
                        open_price=current.open_price if current.time == candle_time else (float(bid_open) if bid_open else close),
                        high=max(current.high, high) if current.time == candle_time else high,
                        low=min(current.low, low) if current.time == candle_time else low,
                        close=close,
                        volume=float(ltv) if ltv else current.volume,
                        completed=False,
                    )

                emit(build_candle_update(current, completed=False))
                logger.debug(
                    "Processed candle update epic=%s resolution=%s item=%s time=%s close=%s completed=%s",
                    epic,
                    resolution,
                    item_name or item_name_expected,
                    current.time,
                    current.close,
                    completed,
                )

            except Exception as e:
                logger.error(f"Error processing candle update: {e}")

        item_name_expected = item_name
        subscription = LightstreamerSubscription(
            mode="MERGE",
            items=[item_name],
            fields=fields
        )

        subscription.addlistener(on_item_update)

        loop = asyncio.get_event_loop()
        raw_sub_key: object | None = await loop.run_in_executor(None, client.subscribe, subscription)
        sub_key = None if raw_sub_key is None else str(raw_sub_key)

        if sub_key:
            self._subscriptions[subscription_key] = sub_key

        logger.info(f"Subscribed to {item_name}")
        return listener_id

    async def unsubscribe(self, epic: str, resolution: str, listener_id: str) -> None:
        subscription_key = f"{epic}:{resolution}"
        listeners = self._listeners.get(subscription_key)
        if listeners is not None:
            listeners.pop(listener_id, None)

        if listeners:
            return

        sub_key = self._subscriptions.get(subscription_key)
        if sub_key and self._client:
            try:
                client = self._client
                if client is None:
                    return
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, client.unsubscribe, sub_key)
            except Exception as e:
                logger.error(f"Error unsubscribing from {epic}: {e}")

        self._subscriptions.pop(subscription_key, None)
        self._listeners.pop(subscription_key, None)

    def get_buffered_candles(self, epic: str, resolution: str, limit: int = 200) -> list[CandleUpdate]:
        candles = stream_candle_buffer.get(epic=epic, resolution=resolution, limit=limit)
        return [
            CandleUpdate(
                epic=candle.epic,
                time=candle.time,
                open_price=candle.open_price,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                completed=candle.completed,
            )
            for candle in candles
        ]


lightstreamer_gateway = LightstreamerGateway()


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
