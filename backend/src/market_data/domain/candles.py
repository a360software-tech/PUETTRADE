from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock


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


class CandleSeriesBuffer:
    def __init__(self, maxlen: int = 500) -> None:
        self._maxlen = maxlen
        self._series: dict[tuple[str, str], deque[BufferedCandle]] = {}
        self._lock = Lock()

    def upsert(self, candle: BufferedCandle) -> None:
        key = (candle.epic, candle.resolution)
        with self._lock:
            series = self._series.setdefault(key, deque(maxlen=self._maxlen))
            if series and series[-1].time == candle.time:
                series[-1] = candle
                return

            if series and _parse_time(candle.time) < _parse_time(series[-1].time):
                return

            series.append(candle)

    def get(self, epic: str, resolution: str, limit: int = 200) -> list[BufferedCandle]:
        key = (epic, resolution)
        with self._lock:
            series = self._series.get(key)
            if series:
                return list(series)[-limit:]

            derived = self._build_derived_series(epic, resolution, limit)
            return derived[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._series.clear()

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
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def _floor_time(value: datetime, resolution_seconds: int) -> datetime:
    epoch = datetime(1970, 1, 1)
    elapsed_seconds = int((value - epoch).total_seconds())
    bucket_seconds = elapsed_seconds - (elapsed_seconds % resolution_seconds)
    return epoch + timedelta(seconds=bucket_seconds)


stream_candle_buffer = CandleSeriesBuffer()
