from fastapi.testclient import TestClient

from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.service import get_positions_service
from src.main import app


def setup_function() -> None:
    get_positions_service().reset()
    stream_candle_buffer.clear()


def test_open_position_from_signal_endpoint() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/positions/from-signal",
        json={
            "epic": "CS.D.EURUSD.CFD.IP",
            "signal": {
                "side": "LONG",
                "price": 1.1012,
                "time": "2026-03-18T12:00:00",
                "reason": "EMA_CROSS_UP",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["position"]
    assert payload["status"] == "OPEN"
    assert payload["side"] == "LONG"


def test_open_live_position_endpoint() -> None:
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
        "/api/v1/positions/CS.D.EURUSD.CFD.IP/open-live",
        json={"resolution": "MINUTE_5", "limit": 20},
    )

    assert response.status_code == 200
    payload = response.json()["position"]
    assert payload["status"] == "OPEN"
    assert payload["side"] == "SHORT"


def test_close_position_endpoint() -> None:
    client = TestClient(app)
    open_response = client.post(
        "/api/v1/positions/from-signal",
        json={
            "epic": "CS.D.EURUSD.CFD.IP",
            "signal": {
                "side": "SHORT",
                "price": 1.1012,
                "time": "2026-03-18T12:00:00",
                "reason": "RSI > 70",
            },
        },
    )
    position_id = open_response.json()["position"]["id"]

    close_response = client.post(
        f"/api/v1/positions/{position_id}/close",
        json={"close_price": 1.1000, "closed_at": "2026-03-18T12:05:00"},
    )

    assert close_response.status_code == 200
    payload = close_response.json()["position"]
    assert payload["status"] == "CLOSED"
    assert payload["pnl_points"] > 0
