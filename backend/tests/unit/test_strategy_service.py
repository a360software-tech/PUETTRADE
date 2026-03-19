from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from strategy.application.dto import StrategyEvaluateRequest
from strategy.application.service import StrategyService
from strategy.domain.indicators import calculate_ema, calculate_rsi
from strategy.domain.models import StrategyManifest, TriggerRule, SignalSide


def test_calculate_ema_returns_values_after_period() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]

    ema = calculate_ema(values, period=3)

    assert ema[:2] == [None, None]
    assert ema[2] == 2.0
    assert ema[-1] is not None


def test_calculate_rsi_detects_overbought_series() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    rsi = calculate_rsi(values, period=3)

    assert rsi[-1] == 100.0


def test_strategy_service_generates_rsi_short_signal() -> None:
    service = StrategyService()
    request = StrategyEvaluateRequest.model_validate(
        {
            "epic": "CS.D.EURUSD.CFD.IP",
            "resolution": "MINUTE_5",
            "candles": [
                {"time": "2026-03-18T12:00:00", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0},
                {"time": "2026-03-18T12:05:00", "open": 1.0, "high": 1.2, "low": 1.0, "close": 2.0},
                {"time": "2026-03-18T12:10:00", "open": 2.0, "high": 2.2, "low": 2.0, "close": 3.0},
                {"time": "2026-03-18T12:15:00", "open": 3.0, "high": 3.2, "low": 3.0, "close": 4.0},
                {"time": "2026-03-18T12:20:00", "open": 4.0, "high": 4.2, "low": 4.0, "close": 5.0},
                {"time": "2026-03-18T12:25:00", "open": 5.0, "high": 5.2, "low": 5.0, "close": 6.0},
            ],
            "manifest": {
                "name": "RSI Short",
                "indicators": {"rsi_period": 3, "fast_ema": 2, "slow_ema": 4},
                "triggers": [{"condition": "RSI > 70", "action": "SHORT"}],
            },
        }
    )

    response = service.evaluate(request)

    assert response.signal is not None
    assert response.signal.side == SignalSide.SHORT
    assert response.signal.reason == "RSI > 70"
    assert response.signal.phase == "RSI_OVERBOUGHT"


def test_strategy_service_supports_ema_cross_rules() -> None:
    service = StrategyService()
    request = StrategyEvaluateRequest.model_validate(
        {
            "epic": "CS.D.EURUSD.CFD.IP",
            "resolution": "MINUTE_5",
            "candles": [
                {"time": "2026-03-18T12:00:00", "open": 10.0, "high": 10.2, "low": 9.8, "close": 10.0},
                {"time": "2026-03-18T12:05:00", "open": 10.0, "high": 10.2, "low": 8.8, "close": 9.0},
                {"time": "2026-03-18T12:10:00", "open": 9.0, "high": 9.2, "low": 7.8, "close": 8.0},
                {"time": "2026-03-18T12:15:00", "open": 8.0, "high": 8.2, "low": 6.8, "close": 7.0},
                {"time": "2026-03-18T12:20:00", "open": 7.0, "high": 7.2, "low": 5.8, "close": 6.0},
                {"time": "2026-03-18T12:25:00", "open": 6.0, "high": 6.2, "low": 4.8, "close": 5.0},
                {"time": "2026-03-18T12:30:00", "open": 5.0, "high": 7.2, "low": 4.8, "close": 7.0},
                {"time": "2026-03-18T12:35:00", "open": 7.0, "high": 11.2, "low": 6.8, "close": 11.0},
            ],
            "manifest": StrategyManifest(
                name="EMA Cross",
                indicators={"rsi_period": 3, "fast_ema": 2, "slow_ema": 5},
                triggers=[TriggerRule(condition="EMA_CROSS_UP", action=SignalSide.LONG)],
            ).model_dump(),
        }
    )

    response = service.evaluate(request)

    assert response.signal is not None
    assert response.signal.side == SignalSide.LONG
    assert response.signal.phase == "EMA_CROSS_BULL"


def test_strategy_service_evaluates_live_buffer() -> None:
    stream_candle_buffer.clear()
    service = StrategyService()

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

    response = service.evaluate_live(epic="CS.D.EURUSD.CFD.IP", resolution="MINUTE_5", limit=20)

    assert response.source == "stream_buffer"
    assert response.status == "ok"
    assert response.candles_analyzed == 20
    assert response.signal is not None
    assert response.signal.side == SignalSide.SHORT


def test_strategy_service_reports_insufficient_live_candles() -> None:
    stream_candle_buffer.clear()
    service = StrategyService()

    for index in range(2):
        stream_candle_buffer.upsert(
            BufferedCandle(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="5MINUTE",
                time=f"2026-03-18T12:{index * 5:02d}:00",
                open_price=1.0,
                high=1.1,
                low=0.9,
                close=1.0,
                volume=10.0,
                completed=True,
            )
        )

    response = service.evaluate_live(epic="CS.D.EURUSD.CFD.IP", resolution="MINUTE_5", limit=20)

    assert response.status == "insufficient_candles"
    assert response.signal is None
    assert response.latest_indicators is None
