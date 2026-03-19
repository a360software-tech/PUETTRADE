from fastapi.testclient import TestClient

from engine.application.service import get_engine_service
from market_data.domain.candles import BufferedCandle, stream_candle_buffer
from positions.application.service import get_positions_service
from safety.application.service import get_safety_service
from src.main import app


def setup_function() -> None:
    get_engine_service().reset()
    get_positions_service().reset()
    get_safety_service().reset()
    stream_candle_buffer.clear()


def test_engine_status_and_start_endpoints() -> None:
    client = TestClient(app)

    start = client.post("/api/v1/engine/start", json={"epics": ["CS.D.EURUSD.CFD.IP"]})
    assert start.status_code == 200
    assert start.json()["mode"] == "RUNNING"
    assert start.json()["active_epics"] == ["CS.D.EURUSD.CFD.IP"]

    status = client.get("/api/v1/engine/status")
    assert status.status_code == 200
    assert status.json()["mode"] == "RUNNING"


def test_engine_run_cycle_endpoint_opens_position() -> None:
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
    client.post("/api/v1/engine/start", json={"epics": ["CS.D.EURUSD.CFD.IP"]})

    response = client.post(
        "/api/v1/engine/run-cycle",
        json={
            "epic": "CS.D.EURUSD.CFD.IP",
            "resolution": "MINUTE_5",
            "limit": 20,
            "settings": {"account_balance": 10000},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "position_opened"
    assert payload["execution"]["provider"] == "paper"
    assert payload["position_id"] is not None
