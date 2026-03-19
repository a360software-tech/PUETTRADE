import asyncio

from engine.application.dto import EngineRunCycleRequest, EngineStartRequest
from engine.application.service import get_engine_service
from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.service import get_positions_service
from safety.application.service import get_safety_service


def setup_function() -> None:
    get_engine_service().reset()
    get_positions_service().reset()
    get_safety_service().reset()
    stream_candle_buffer.clear()


def test_engine_run_cycle_opens_position_when_signal_and_risk_align() -> None:
    service = get_engine_service()
    service.start(EngineStartRequest(epics=["CS.D.EURUSD.CFD.IP"]))

    for index in range(25):
        stream_candle_buffer.upsert(
            BufferedCandle(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="5MINUTE",
                time=f"2026-03-18T{12 + (index // 12):02d}:{(index % 12) * 5:02d}:00",
                open_price=1.0 + index,
                high=1.1 + index,
                low=0.9 + index,
                close=1.0 + index,
                volume=10.0,
                completed=True,
            )
        )

    response = asyncio.run(
        service.run_cycle(
            EngineRunCycleRequest(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="MINUTE_5",
                limit=20,
                settings={"account_balance": 10000},
            )
        )
    )

    assert response.action == "position_opened"
    assert response.position_id is not None
    assert response.execution is not None
    assert response.execution.provider == "paper"
    assert response.state.last_position_id == response.position_id


def test_engine_run_cycle_skips_duplicate_signal() -> None:
    service = get_engine_service()
    service.start(EngineStartRequest(epics=["CS.D.EURUSD.CFD.IP"]))

    for index in range(25):
        stream_candle_buffer.upsert(
            BufferedCandle(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="5MINUTE",
                time=f"2026-03-18T{12 + (index // 12):02d}:{(index % 12) * 5:02d}:00",
                open_price=1.0 + index,
                high=1.1 + index,
                low=0.9 + index,
                close=1.0 + index,
                volume=10.0,
                completed=True,
            )
        )

    first = asyncio.run(
        service.run_cycle(
            EngineRunCycleRequest(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="MINUTE_5",
                limit=20,
                settings={"account_balance": 10000},
            )
        )
    )
    second = asyncio.run(
        service.run_cycle(
            EngineRunCycleRequest(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="MINUTE_5",
                limit=20,
                settings={"account_balance": 10000},
            )
        )
    )

    assert first.action == "position_opened"
    assert second.action in {"duplicate_signal_skipped", "position_exists", "blocked_by_safety"}


def test_engine_requires_start_before_cycle() -> None:
    service = get_engine_service()

    try:
        asyncio.run(
            service.run_cycle(
                EngineRunCycleRequest(
                    epic="CS.D.EURUSD.CFD.IP",
                    resolution="MINUTE_5",
                    limit=20,
                    settings={"account_balance": 10000},
                )
            )
        )
    except Exception as exc:
        assert str(exc) == "Engine is stopped. Start it before running cycles."
    else:
        raise AssertionError("Expected stopped engine to reject cycle")
