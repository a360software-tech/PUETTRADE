from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.dto import CreatePositionFromSignalRequest, OpenLivePositionRequest
from positions.application.service import get_positions_service
from positions.domain.models import PositionStatus
from strategy.domain.models import SignalSide, StrategySignal


def setup_function() -> None:
    get_positions_service().reset()
    stream_candle_buffer.clear()


def test_positions_service_opens_and_closes_manual_signal() -> None:
    service = get_positions_service()

    position = service.open_from_signal(
        CreatePositionFromSignalRequest(
            epic="CS.D.EURUSD.CFD.IP",
            signal=StrategySignal(
                side=SignalSide.LONG,
                price=1.1012,
                time="2026-03-18T12:00:00",
                reason="EMA_CROSS_UP",
            ),
        )
    )

    assert position.status == PositionStatus.OPEN

    closed = service.close_position(position.id, close_price=1.1022, closed_at="2026-03-18T12:05:00")

    assert closed.status == PositionStatus.CLOSED
    assert closed.pnl_points is not None
    assert abs(closed.pnl_points - 0.001) < 1e-9


def test_positions_service_opens_from_live_signal() -> None:
    service = get_positions_service()

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

    position = service.open_live(
        "CS.D.EURUSD.CFD.IP",
        OpenLivePositionRequest(resolution="MINUTE_5", limit=20),
    )

    assert position.status == PositionStatus.OPEN
    assert position.side == "SHORT"


def test_positions_service_prevents_duplicate_open_position_per_epic() -> None:
    service = get_positions_service()
    request = CreatePositionFromSignalRequest(
        epic="CS.D.EURUSD.CFD.IP",
        signal=StrategySignal(
            side=SignalSide.SHORT,
            price=1.1012,
            time="2026-03-18T12:00:00",
            reason="RSI > 70",
        ),
    )

    service.open_from_signal(request)

    try:
        service.open_from_signal(request)
    except Exception as exc:
        assert str(exc) == "There is already an open position for CS.D.EURUSD.CFD.IP"
    else:
        raise AssertionError("Expected duplicate open position to fail")
