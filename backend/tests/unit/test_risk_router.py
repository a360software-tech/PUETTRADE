from fastapi.testclient import TestClient

from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.service import get_positions_service
from src.main import app


def setup_function() -> None:
    get_positions_service().reset()
    stream_candle_buffer.clear()


def test_risk_evaluate_endpoint_returns_plan() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/risk/evaluate",
        json={
            "epic": "CS.D.EURUSD.CFD.IP",
            "signal": {
                "side": "SHORT",
                "price": 1.1050,
                "time": "2026-03-18T12:00:00",
                "momentum": 75.0,
                "reason": "RSI > 70",
            },
            "settings": {"account_balance": 10000},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["approved"] is True
    assert payload["decision"]["plan"]["size"] > 0


def test_risk_open_live_position_endpoint_opens_position() -> None:
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
    response = client.post(
        "/api/v1/risk/CS.D.EURUSD.CFD.IP/open-live-position",
        json={
            "resolution": "MINUTE_5",
            "limit": 20,
            "settings": {"account_balance": 10000},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["approved"] is True
    assert payload["position"]["side"] == "SHORT"
    assert payload["position"]["size"] > 0
