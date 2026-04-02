from datetime import UTC, datetime

from market_data.application.dto import CandleItemResponse, Resolution
from market_data.domain.candles import BufferedCandle, candle_close_notifier, to_lightstreamer_resolution
from shared.infrastructure.persistence import DatabasePersistence, get_persistence


class CandleRepository:
    def __init__(self, persistence: DatabasePersistence | None = None) -> None:
        self._persistence = persistence or get_persistence()

    def upsert_many(self, epic: str, resolution: Resolution, candles: list[CandleItemResponse], *, source: str) -> None:
        if not candles:
            return

        buffered_resolution = to_lightstreamer_resolution(resolution)
        for candle in candles:
            self._persistence.upsert_candle(
                epic=epic,
                resolution=buffered_resolution,
                time=candle.time,
                open_price=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=0.0 if candle.volume is None else candle.volume,
            )

        self._persistence.save_candle_sync_state(
            epic=epic,
            resolution=buffered_resolution,
            status="SYNCED",
            last_synced_at=_utc_now_iso(),
            last_candle_time=candles[-1].time,
            source=source,
        )

    def upsert_buffered_candle(self, candle: BufferedCandle, *, source: str) -> None:
        self._persistence.upsert_candle(
            epic=candle.epic,
            resolution=candle.resolution,
            time=candle.time,
            open_price=candle.open_price,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
        self._persistence.save_candle_sync_state(
            epic=candle.epic,
            resolution=candle.resolution,
            status="SYNCED",
            last_synced_at=_utc_now_iso(),
            last_candle_time=candle.time,
            source=source,
        )

    def get_candles(
        self,
        epic: str,
        resolution: Resolution,
        *,
        limit: int = 200,
        from_time: str | None = None,
        to_time: str | None = None,
    ) -> list[CandleItemResponse]:
        buffered_resolution = to_lightstreamer_resolution(resolution)
        rows = self._persistence.load_candles(
            epic=epic,
            resolution=buffered_resolution,
            limit=limit,
            from_time=from_time,
            to_time=to_time,
        )
        return [
            CandleItemResponse(
                time=str(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for row in rows
        ]

    def get_latest_candle_time(self, epic: str, resolution: Resolution) -> str | None:
        return self._persistence.get_latest_candle_time(
            epic=epic,
            resolution=to_lightstreamer_resolution(resolution),
        )

    def get_sync_state(self, epic: str, resolution: Resolution) -> dict[str, object] | None:
        return self._persistence.load_candle_sync_state(
            epic=epic,
            resolution=to_lightstreamer_resolution(resolution),
        )


_repository: CandleRepository | None = None
_listener_id: str | None = None


def get_candle_repository() -> CandleRepository:
    global _repository, _listener_id
    if _repository is None:
        _repository = CandleRepository()
    if _listener_id is None:
        _listener_id = candle_close_notifier.register(
            lambda candle: get_candle_repository().upsert_buffered_candle(candle, source="stream")
        )
    return _repository


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
