import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import httpx

from lightstreamer_client import LightstreamerClient, LightstreamerSubscription

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
        self._candle_state: dict[str, dict] = {}
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

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._client.connect)

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
            self._candle_state.clear()

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
        callback: Callable[[CandleUpdate], None] = None
    ) -> Optional[str]:
        if not callback:
            raise ValueError("callback is required")
        
        if not self._client or not self._connected:
            raise RuntimeError("Not connected to Lightstreamer")

        sub_key = self._subscriptions.get(epic)
        if sub_key:
            return sub_key

        item_name = f"CHART:{epic}:{resolution}"
        fields = ["BID_OPEN", "BID_HIGH", "BID_LOW", "BID_CLOSE", "CONS_END", "UTM", "LTV"]

        current_candle: dict = {}
        
        def on_item_update(update) -> None:
            try:
                bid_open = update.get("BID_OPEN")
                bid_high = update.get("BID_HIGH")
                bid_low = update.get("BID_LOW")
                bid_close = update.get("BID_CLOSE")
                cons_end = update.get("CONS_END")
                utm = update.get("UTM")

                if not bid_close:
                    return

                completed = cons_end == "1" if cons_end else False

                timestamp_ms = int(utm) if utm else int(datetime.now().timestamp() * 1000)
                candle_time = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%dT%H:%M:%S")

                if completed and current_candle:
                    callback(CandleUpdate(
                        epic=epic,
                        time=current_candle["time"],
                        open_price=current_candle["open"],
                        high=current_candle["high"],
                        low=current_candle["low"],
                        close=current_candle["close"],
                        volume=current_candle.get("volume", 0.0),
                        completed=True
                    ))
                    current_candle.clear()

                if not current_candle:
                    current_candle = {
                        "time": candle_time,
                        "open": float(bid_open) if bid_open else 0.0,
                        "high": float(bid_high) if bid_high else 0.0,
                        "low": float(bid_low) if bid_low else 0.0,
                        "close": float(bid_close) if bid_close else 0.0,
                        "volume": 0.0
                    }
                else:
                    close = float(bid_close) if bid_close else 0.0
                    current_candle["close"] = close
                    current_candle["high"] = max(current_candle["high"], close)
                    current_candle["low"] = min(current_candle["low"], close)

                callback(CandleUpdate(
                    epic=epic,
                    time=current_candle["time"],
                    open_price=current_candle["open"],
                    high=current_candle["high"],
                    low=current_candle["low"],
                    close=current_candle["close"],
                    volume=current_candle.get("volume", 0.0),
                    completed=False
                ))

            except Exception as e:
                logger.error(f"Error processing candle update: {e}")

        subscription = LightstreamerSubscription(
            mode="MERGE",
            items=[item_name],
            fields=fields
        )

        subscription.addlistener(on_item_update)

        loop = asyncio.get_event_loop()
        sub_key: Optional[str] = await loop.run_in_executor(
            None,
            lambda: self._client.subscribe(subscription)
        )

        if sub_key:
            self._subscriptions[epic] = sub_key
            self._candle_state[epic] = current_candle

        logger.info(f"Subscribed to {item_name}")
        return sub_key

    async def unsubscribe(self, epic: str) -> None:
        sub_key = self._subscriptions.get(epic)
        if sub_key and self._client:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: self._client.unsubscribe(sub_key))
            except Exception as e:
                logger.error(f"Error unsubscribing from {epic}: {e}")

        self._subscriptions.pop(epic, None)
        self._candle_state.pop(epic, None)


lightstreamer_gateway = LightstreamerGateway()
