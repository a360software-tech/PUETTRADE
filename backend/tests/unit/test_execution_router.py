from fastapi.testclient import TestClient

from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.service import get_positions_service
from safety.application.service import get_safety_service
from src.main import app


def setup_function() -> None:
    get_positions_service().reset()
    get_safety_service().reset()
    stream_candle_buffer.clear()


def test_execution_open_position_endpoint_executes_paper_trade() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/execution/open-position",
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
    assert payload["execution"]["provider"] == "paper"
    assert payload["position"]["execution_provider"] == "paper"


def test_execution_open_live_position_endpoint_executes_paper_trade() -> None:
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
        "/api/v1/execution/CS.D.EURUSD.CFD.IP/open-live-position",
        json={
            "resolution": "MINUTE_5",
            "limit": 20,
            "settings": {"account_balance": 10000},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["position"]["side"] == "SHORT"
    assert payload["execution"]["status"] == "FILLED"


def test_execution_close_position_endpoint_closes_paper_trade() -> None:
    client = TestClient(app)
    open_response = client.post(
        "/api/v1/execution/open-position",
        json={
            "epic": "CS.D.EURUSD.CFD.IP",
            "signal": {
                "side": "LONG",
                "price": 1.1010,
                "time": "2026-03-18T12:00:00",
                "momentum": 30.0,
                "reason": "RSI < 30",
            },
            "settings": {"account_balance": 10000},
        },
    )
    position_id = open_response.json()["position"]["id"]

    close_response = client.post(
        f"/api/v1/execution/{position_id}/close",
        json={"close_price": 1.1020, "closed_at": "2026-03-18T12:05:00"},
    )

    assert close_response.status_code == 200
    payload = close_response.json()
    assert payload["execution"]["provider"] == "paper"
    assert payload["position"]["status"] == "CLOSED"
