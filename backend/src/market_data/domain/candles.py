from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from typing import Callable, Iterable
from threading import Lock
from uuid import uuid4


@dataclass(slots=True)
class BufferedCandle:
    epic: str
    resolution: str
    time: str
    open_price: float
    high: float
    low: float
    close: float
    volume: float
    completed: bool

    @property
    def open_time(self) -> str:
        return self.time

    @property
    def close_time(self) -> str | None:
        resolution_seconds = _LIGHTSTREAMER_TO_SECONDS.get(self.resolution)
        if resolution_seconds is None:
            return None
        start = _parse_time(self.time)
        if start == datetime.min:
            return None
        return (start + timedelta(seconds=resolution_seconds)).strftime("%Y-%m-%dT%H:%M:%S")


_RESOLUTION_TO_LIGHTSTREAMER: dict[str, str] = {
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

_LIGHTSTREAMER_TO_SECONDS: dict[str, int] = {
    "1MINUTE": 60,
    "2MINUTE": 120,
    "3MINUTE": 180,
    "5MINUTE": 300,
    "10MINUTE": 600,
    "15MINUTE": 900,
    "30MINUTE": 1800,
    "1HOUR": 3600,
    "2HOUR": 7200,
    "3HOUR": 10800,
    "4HOUR": 14400,
    "1DAY": 86400,
}


def to_lightstreamer_resolution(resolution: str) -> str:
    return _RESOLUTION_TO_LIGHTSTREAMER.get(resolution, "1MINUTE")


def supports_buffered_resolution(resolution: str) -> bool:
    return resolution in _RESOLUTION_TO_LIGHTSTREAMER or resolution in _LIGHTSTREAMER_TO_SECONDS


def resolution_seconds(resolution: str) -> int | None:
    return _LIGHTSTREAMER_TO_SECONDS.get(resolution)


@dataclass(slots=True)
class TickInput:
    epic: str
    price: float
    timestamp: float | int | str | datetime
    volume: float = 0.0


class CandleCloseNotifier:
    def __init__(self) -> None:
        self._listeners: dict[str, Callable[[BufferedCandle], None]] = {}
        self._lock = Lock()

    def register(self, listener: Callable[[BufferedCandle], None]) -> str:
        listener_id = str(uuid4())
        with self._lock:
            self._listeners[listener_id] = listener
        return listener_id

    def unregister(self, listener_id: str) -> None:
        with self._lock:
            self._listeners.pop(listener_id, None)

    def notify(self, candle: BufferedCandle) -> None:
        with self._lock:
            listeners = list(self._listeners.values())
        for listener in listeners:
            listener(candle)


class TickCandleBuilder:
    def __init__(
        self,
        *,
        buffer: "CandleSeriesBuffer | None" = None,
        notifier: CandleCloseNotifier | None = None,
        resolutions: list[str] | None = None,
    ) -> None:
        self._buffer = buffer or stream_candle_buffer
        self._notifier = notifier or candle_close_notifier
        self._resolutions = resolutions or ["1MINUTE", "5MINUTE"]

    def update_with_tick(self, tick: TickInput) -> list[BufferedCandle]:
        tick_timestamp = _parse_timestamp_input(tick.timestamp)
        closed: list[BufferedCandle] = []

        for resolution in self._resolutions:
            tf_seconds = resolution_seconds(resolution)
            if tf_seconds is None:
                continue

            bucket_start = _floor_epoch_seconds(tick_timestamp, tf_seconds)
            bucket_time = datetime.fromtimestamp(bucket_start, UTC).strftime("%Y-%m-%dT%H:%M:%S")
            current = self._buffer.get_current(tick.epic, resolution)

            if current is None:
                self._buffer.upsert(
                    BufferedCandle(
                        epic=tick.epic,
                        resolution=resolution,
                        time=bucket_time,
                        open_price=tick.price,
                        high=tick.price,
                        low=tick.price,
                        close=tick.price,
                        volume=tick.volume,
                        completed=False,
                    )
                )
                continue

            current_start = _parse_time(current.time)
            if current_start == datetime.min:
                continue
            current_epoch = _datetime_to_epoch_seconds(current_start)

            if current_epoch == bucket_start:
                self._buffer.upsert(
                    BufferedCandle(
                        epic=current.epic,
                        resolution=current.resolution,
                        time=current.time,
                        open_price=current.open_price,
                        high=max(current.high, tick.price),
                        low=min(current.low, tick.price),
                        close=tick.price,
                        volume=current.volume + tick.volume,
                        completed=False,
                    )
                )
                continue

            if bucket_start > current_epoch:
                completed = BufferedCandle(
                    epic=current.epic,
                    resolution=current.resolution,
                    time=current.time,
                    open_price=current.open_price,
                    high=current.high,
                    low=current.low,
                    close=current.close,
                    volume=current.volume,
                    completed=True,
                )
                self._buffer.upsert(completed)
                self._notifier.notify(completed)
                closed.append(completed)

                self._buffer.upsert(
                    BufferedCandle(
                        epic=tick.epic,
                        resolution=resolution,
                        time=bucket_time,
                        open_price=tick.price,
                        high=tick.price,
                        low=tick.price,
                        close=tick.price,
                        volume=tick.volume,
                        completed=False,
                    )
                )

        return closed

    def generate_fake_history(
        self,
        epic: str,
        *,
        resolution: str,
        count: int = 100,
        start_price: float = 1.0,
        seed: int = 7,
    ) -> list[BufferedCandle]:
        tf_seconds = resolution_seconds(resolution)
        if tf_seconds is None:
            return []

        randomizer = Random(seed)
        now = int(datetime.now(UTC).timestamp())
        start_epoch = now - (count * tf_seconds)
        candles: list[BufferedCandle] = []
        current_price = start_price

        for index in range(count):
            candle_start = _floor_epoch_seconds(start_epoch + (index * tf_seconds), tf_seconds)
            open_price = current_price
            close_price = open_price * randomizer.uniform(0.9995, 1.0005)
            high = max(open_price, close_price) * 1.0001
            low = min(open_price, close_price) * 0.9999
            candles.append(
                BufferedCandle(
                    epic=epic,
                    resolution=resolution,
                    time=datetime.fromtimestamp(candle_start, UTC).strftime("%Y-%m-%dT%H:%M:%S"),
                    open_price=open_price,
                    high=high,
                    low=low,
                    close=close_price,
                    volume=float(randomizer.randint(100, 1000)),
                    completed=True,
                )
            )
            current_price = close_price

        self._buffer.seed_completed(candles)
        return candles


class CandleSeriesBuffer:
    def __init__(self, maxlen: int = 500) -> None:
        self._maxlen = maxlen
        self._series: dict[tuple[str, str], deque[BufferedCandle]] = {}
        self._current: dict[tuple[str, str], BufferedCandle] = {}
        self._lock = Lock()

    def upsert(self, candle: BufferedCandle) -> None:
        key = (candle.epic, candle.resolution)
        with self._lock:
            if candle.completed:
                self._current.pop(key, None)
            else:
                self._current[key] = candle
            series = self._series.setdefault(key, deque(maxlen=self._maxlen))
            if series and series[-1].time == candle.time:
                series[-1] = candle
                return

            if series and _parse_time(candle.time) < _parse_time(series[-1].time):
                return

            series.append(candle)

    def seed_completed(self, candles: Iterable[BufferedCandle]) -> None:
        for candle in candles:
            seeded = BufferedCandle(
                epic=candle.epic,
                resolution=candle.resolution,
                time=candle.time,
                open_price=candle.open_price,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                completed=True,
            )
            self.upsert(seeded)

    def get(self, epic: str, resolution: str, limit: int = 200) -> list[BufferedCandle]:
        return self.get_series(epic=epic, resolution=resolution, limit=limit, include_incomplete=True)

    def get_series(
        self,
        epic: str,
        resolution: str,
        limit: int = 200,
        *,
        include_incomplete: bool = True,
    ) -> list[BufferedCandle]:
        key = (epic, resolution)
        with self._lock:
            series = self._series.get(key)
            if series:
                candles = list(series)
                if not include_incomplete:
                    candles = [candle for candle in candles if candle.completed]
                return candles[-limit:]

            derived = self._build_derived_series(epic, resolution, limit)
            if not include_incomplete:
                derived = [candle for candle in derived if candle.completed]
            return derived[-limit:]

    def get_current(self, epic: str, resolution: str) -> BufferedCandle | None:
        key = (epic, resolution)
        with self._lock:
            current = self._current.get(key)
            if current is not None and not current.completed:
                return current

            series = self._series.get(key)
            if not series:
                return None

            last = series[-1]
            if last.completed:
                return None
            return last

    def get_last_completed(self, epic: str, resolution: str) -> BufferedCandle | None:
        candles = self.get_series(epic=epic, resolution=resolution, limit=1, include_incomplete=False)
        if not candles:
            return None
        return candles[-1]

    def clear(self) -> None:
        with self._lock:
            self._series.clear()
            self._current.clear()

    def _build_derived_series(self, epic: str, target_resolution: str, limit: int) -> list[BufferedCandle]:
        target_seconds = _LIGHTSTREAMER_TO_SECONDS.get(target_resolution)
        if target_seconds is None:
            return []

        candidates: list[tuple[int, deque[BufferedCandle]]] = []
        for (series_epic, source_resolution), candles in self._series.items():
            if series_epic != epic:
                continue
            source_seconds = _LIGHTSTREAMER_TO_SECONDS.get(source_resolution)
            if source_seconds is None:
                continue
            if source_seconds >= target_seconds or target_seconds % source_seconds != 0:
                continue
            completed = [candle for candle in candles if candle.completed]
            if completed:
                candidates.append((source_seconds, deque(completed, maxlen=len(completed))))

        if not candidates:
            return []

        source_seconds, source_series = min(candidates, key=lambda item: item[0])
        ratio = target_seconds // source_seconds
        if ratio <= 1:
            return list(source_series)[-limit:]

        aggregated: list[BufferedCandle] = []
        bucket: list[BufferedCandle] = []
        bucket_start: datetime | None = None

        for candle in source_series:
            candle_time = _parse_time(candle.time)
            current_bucket = _floor_time(candle_time, target_seconds)

            if bucket_start is None or current_bucket != bucket_start:
                if bucket and bucket_start is not None:
                    current_start = bucket_start
                    aggregated.append(_aggregate_bucket(epic, target_resolution, current_start, bucket, ratio))
                bucket_start = current_bucket
                bucket = [candle]
                continue

            bucket.append(candle)

        if bucket and bucket_start is not None:
            current_start = bucket_start
            aggregated.append(_aggregate_bucket(epic, target_resolution, current_start, bucket, ratio))

        return aggregated[-limit:]


def _aggregate_bucket(
    epic: str,
    resolution: str,
    bucket_start: datetime,
    candles: list[BufferedCandle],
    expected_count: int,
) -> BufferedCandle:
    first = candles[0]
    last = candles[-1]

    return BufferedCandle(
        epic=epic,
        resolution=resolution,
        time=bucket_start.strftime("%Y-%m-%dT%H:%M:%S"),
        open_price=first.open_price,
        high=max(candle.high for candle in candles),
        low=min(candle.low for candle in candles),
        close=last.close,
        volume=sum(candle.volume for candle in candles),
        completed=len(candles) >= expected_count and all(candle.completed for candle in candles),
    )


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed
    except ValueError:
        return datetime.min


def _parse_timestamp_input(value: float | int | str | datetime) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        parsed = _parse_time(value)
        if parsed != datetime.min:
            return parsed.timestamp()
        try:
            return float(value)
        except ValueError:
            return datetime.now(UTC).timestamp()
    return datetime.now(UTC).timestamp()


def _floor_time(value: datetime, resolution_seconds: int) -> datetime:
    epoch = datetime(1970, 1, 1)
    elapsed_seconds = int((value - epoch).total_seconds())
    bucket_seconds = elapsed_seconds - (elapsed_seconds % resolution_seconds)
    return epoch + timedelta(seconds=bucket_seconds)


def _floor_epoch_seconds(timestamp: float, resolution_seconds: int) -> int:
    raw_seconds = int(timestamp)
    return raw_seconds - (raw_seconds % resolution_seconds)


def _datetime_to_epoch_seconds(value: datetime) -> int:
    if value.tzinfo is not None:
        return int(value.astimezone(UTC).timestamp())
    return int(value.replace(tzinfo=UTC).timestamp())


stream_candle_buffer = CandleSeriesBuffer()
candle_close_notifier = CandleCloseNotifier()
tick_candle_builder = TickCandleBuilder(buffer=stream_candle_buffer, notifier=candle_close_notifier)
