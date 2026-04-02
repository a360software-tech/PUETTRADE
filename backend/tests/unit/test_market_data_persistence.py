import asyncio
from pathlib import Path

from market_data.application.history_service import reseed_buffer_from_persistence
from market_data.application.dto import CandleItemResponse, CandleQuery
from market_data.application.service import MarketDataService
from market_data.infrastructure.candle_repository import CandleRepository
from shared.config.settings import Settings
from shared.infrastructure.persistence import DatabasePersistence
from strategy.application.sources import StreamBufferStrategyCandleSource


class _AuthStub:
    async def get_session_tokens(self):
        raise RuntimeError("session tokens should not be requested for persisted reads")


def test_candle_repository_roundtrip_and_buffer_reseed(tmp_path: Path) -> None:
    persistence = DatabasePersistence(tmp_path / "candles.sqlite3")
    repository = CandleRepository(persistence)

    repository.upsert_many(
        "CS.D.EURUSD.CFD.IP",
        "MINUTE_5",
        [
            CandleItemResponse(time="2026-03-18T12:00:00", open=1.1, high=1.2, low=1.0, close=1.15, volume=10.0),
            CandleItemResponse(time="2026-03-18T12:05:00", open=1.15, high=1.25, low=1.1, close=1.2, volume=11.0),
        ],
        source="test",
    )

    candles = repository.get_candles("CS.D.EURUSD.CFD.IP", "MINUTE_5", limit=10)
    reseeded = reseed_buffer_from_persistence(repository, "CS.D.EURUSD.CFD.IP", "MINUTE_5", 10)
    sync_state = repository.get_sync_state("CS.D.EURUSD.CFD.IP", "MINUTE_5")

    assert len(candles) == 2
    assert len(reseeded) == 2
    assert sync_state is not None
    assert sync_state["status"] == "SYNCED"


def test_market_data_service_reads_persisted_candles_without_auth(tmp_path: Path) -> None:
    persistence = DatabasePersistence(tmp_path / "candles-service.sqlite3")
    repository = CandleRepository(persistence)
    repository.upsert_many(
        "CS.D.EURUSD.CFD.IP",
        "MINUTE_5",
        [
            CandleItemResponse(
                time=f"2026-03-18T12:{index * 5:02d}:00",
                open=1.1 + (index * 0.001),
                high=1.11 + (index * 0.001),
                low=1.09 + (index * 0.001),
                close=1.105 + (index * 0.001),
                volume=10.0 + index,
            )
            for index in range(3)
        ],
        source="test",
    )
    service = MarketDataService(Settings(), repository=repository)

    response = asyncio.run(
        service.get_candles(
            epic="CS.D.EURUSD.CFD.IP",
            query=CandleQuery(resolution="MINUTE_5", max=3, from_=None, to=None),
            access_token=None,
            auth_service=_AuthStub(),
        )
    )

    assert len(response.candles) == 3
    assert response.candles[0].time == "2026-03-18T12:00:00"


def test_strategy_source_falls_back_to_persisted_candles(tmp_path: Path) -> None:
    persistence = DatabasePersistence(tmp_path / "strategy-candles.sqlite3")
    repository = CandleRepository(persistence)
    repository.upsert_many(
        "CS.D.EURUSD.CFD.IP",
        "MINUTE_5",
        [
            CandleItemResponse(
                time=f"2026-03-18T12:{index * 5:02d}:00",
                open=1.1 + (index * 0.001),
                high=1.11 + (index * 0.001),
                low=1.09 + (index * 0.001),
                close=1.105 + (index * 0.001),
                volume=10.0 + index,
            )
            for index in range(6)
        ],
        source="test",
    )

    source = StreamBufferStrategyCandleSource(repository=repository)
    candles = source.get_candles("CS.D.EURUSD.CFD.IP", "MINUTE_5", 5)

    assert len(candles) == 5
    assert candles[-1].time == "2026-03-18T12:25:00"
