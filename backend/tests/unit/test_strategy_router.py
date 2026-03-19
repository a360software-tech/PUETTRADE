from fastapi.testclient import TestClient

from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from src.main import app


def test_strategy_evaluate_endpoint_returns_signal_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/strategy/evaluate",
        json={
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
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["epic"] == "CS.D.EURUSD.CFD.IP"
    assert payload["signal"]["side"] == "SHORT"
    assert payload["signal"]["phase"] == "RSI_OVERBOUGHT"


def test_strategy_live_signal_endpoint_reads_buffered_candles() -> None:
    stream_candle_buffer.clear()
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

    client = TestClient(app)
    response = client.get("/api/v1/strategy/CS.D.EURUSD.CFD.IP/signal?resolution=MINUTE_5&limit=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "stream_buffer"
    assert payload["status"] == "ok"
    assert payload["candles_analyzed"] == 20
    assert payload["signal"]["side"] == "SHORT"
