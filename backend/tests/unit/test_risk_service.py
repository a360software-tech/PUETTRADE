from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.dto import CreatePositionFromSignalRequest
from positions.application.service import get_positions_service
from risk.application.dto import EvaluateLiveRiskRequest, EvaluateRiskRequest
from risk.application.service import get_risk_service
from risk.domain.models import RiskSettings
from strategy.domain.models import SignalSide, StrategySignal


def setup_function() -> None:
    get_positions_service().reset()
    stream_candle_buffer.clear()


def test_risk_service_approves_manual_signal_and_builds_plan() -> None:
    service = get_risk_service()

    response = service.evaluate_signal(
        EvaluateRiskRequest(
            epic="CS.D.EURUSD.CFD.IP",
            signal=StrategySignal(
                side=SignalSide.SHORT,
                price=1.1050,
                time="2026-03-18T12:00:00",
                momentum=75.0,
                reason="RSI > 70",
            ),
            settings=RiskSettings(account_balance=10000),
        )
    )

    assert response.decision.approved is True
    assert response.decision.plan is not None
    assert response.decision.plan.size > 0


def test_risk_service_rejects_duplicate_open_position() -> None:
    positions_service = get_positions_service()
    positions_service.open_from_signal(
        CreatePositionFromSignalRequest(
            epic="CS.D.EURUSD.CFD.IP",
            signal=StrategySignal(
                side=SignalSide.LONG,
                price=1.101,
                time="2026-03-18T12:00:00",
                reason="EMA_CROSS_UP",
            ),
        )
    )

    service = get_risk_service()
    response = service.evaluate_signal(
        EvaluateRiskRequest(
            epic="CS.D.EURUSD.CFD.IP",
            signal=StrategySignal(
                side=SignalSide.SHORT,
                price=1.1050,
                time="2026-03-18T12:05:00",
                momentum=75.0,
                reason="RSI > 70",
            ),
            settings=RiskSettings(account_balance=10000),
        )
    )

    assert response.decision.approved is False
    assert "already an open position" in response.decision.reason


def test_risk_service_opens_validated_live_position() -> None:
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

    service = get_risk_service()
    response = service.open_validated_live(
        "CS.D.EURUSD.CFD.IP",
        EvaluateLiveRiskRequest(
            resolution="MINUTE_5",
            limit=20,
            settings=RiskSettings(account_balance=10000),
        ),
    )

    assert response.decision.approved is True
    assert response.position.side == "SHORT"
    assert response.position.stop_loss is not None
    assert response.position.take_profit is not None
