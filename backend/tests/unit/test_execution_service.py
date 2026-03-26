import asyncio

from execution.application.dto import CloseExecutionRequest, ExecuteLiveRequest, ExecuteSignalRequest
from execution.application.service import execution_event_notifier, execution_rejection_notifier, get_execution_service
from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.service import get_positions_service
from shared.domain.events import ExecutionRecordedEvent, ExecutionRejectedEvent


def setup_function() -> None:
    get_positions_service().reset()
    stream_candle_buffer.clear()


def test_execution_service_executes_manual_signal_in_paper_mode() -> None:
    service = get_execution_service()

    response = asyncio.run(
        service.execute_from_signal(
            ExecuteSignalRequest(
                epic="CS.D.EURUSD.CFD.IP",
                signal={
                    "side": "SHORT",
                    "price": 1.1050,
                    "time": "2026-03-18T12:00:00",
                    "momentum": 75.0,
                    "reason": "RSI > 70",
                },
                settings={"account_balance": 10000},
            )
        )
    )

    assert response.execution.provider == "paper"
    assert response.position.execution_provider == "paper"
    assert response.position.size is not None
    assert response.position.execution_context is not None
    assert response.position.execution_context["execution_mode"] == "paper"


def test_execution_service_executes_live_signal_in_paper_mode() -> None:
    service = get_execution_service()

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
        service.execute_live(
            "CS.D.EURUSD.CFD.IP",
            ExecuteLiveRequest(
                resolution="MINUTE_5",
                limit=20,
                settings={"account_balance": 10000},
            ),
        )
    )

    assert response.execution.status == "FILLED"
    assert response.position.side == "SHORT"


def test_execution_service_closes_paper_position() -> None:
    service = get_execution_service()
    opened = asyncio.run(
        service.execute_from_signal(
            ExecuteSignalRequest(
                epic="CS.D.EURUSD.CFD.IP",
                signal={
                    "side": "LONG",
                    "price": 1.1010,
                    "time": "2026-03-18T12:00:00",
                    "momentum": 30.0,
                    "reason": "RSI < 30",
                },
                settings={"account_balance": 10000},
            )
        )
    )

    closed = asyncio.run(
        service.close_position(
            opened.position.id,
            CloseExecutionRequest(close_price=1.1020, closed_at="2026-03-18T12:05:00"),
        )
    )

    assert closed.execution.provider == "paper"
    assert closed.position.status == "CLOSED"


def test_execution_service_emits_execution_events() -> None:
    service = get_execution_service()
    events: list[ExecutionRecordedEvent] = []
    listener_id = execution_event_notifier.register(events.append)

    opened = asyncio.run(
        service.execute_from_signal(
            ExecuteSignalRequest(
                epic="CS.D.EURUSD.CFD.IP",
                signal={
                    "side": "SHORT",
                    "price": 1.1050,
                    "time": "2026-03-18T12:00:00",
                    "momentum": 75.0,
                    "reason": "RSI > 70",
                },
                settings={"account_balance": 10000},
            )
        )
    )
    asyncio.run(
        service.close_position(
            opened.position.id,
            CloseExecutionRequest(close_price=1.1040, closed_at="2026-03-18T12:05:00"),
        )
    )
    execution_event_notifier.unregister(listener_id)

    assert len(events) == 2
    assert events[0].action == "open_signal"
    assert events[1].action == "close_position"


def test_execution_service_emits_rejection_event_for_invalid_signal() -> None:
    service = get_execution_service()
    events: list[ExecutionRejectedEvent] = []
    listener_id = execution_rejection_notifier.register(events.append)

    try:
        asyncio.run(
            service.process_signal(
                ExecuteSignalRequest(
                    epic="CS.D.EURUSD.CFD.IP",
                    signal={
                        "side": "SHORT",
                        "price": -1.0,
                        "time": "2026-03-18T12:00:00",
                        "momentum": 75.0,
                        "reason": "RSI > 70",
                    },
                    settings={"account_balance": 10000},
                )
            )
        )
    except Exception:
        pass
    finally:
        execution_rejection_notifier.unregister(listener_id)

    assert len(events) == 1
    assert events[0].action == "open_signal"
