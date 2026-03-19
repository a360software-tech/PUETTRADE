from fastapi.testclient import TestClient

from positions.application.service import get_positions_service
from safety.application.service import get_safety_service
from src.main import app


def setup_function() -> None:
    get_positions_service().reset()
    get_safety_service().reset()


def test_safety_status_endpoint_returns_operational_report() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/safety/status?epic=CS.D.EURUSD.CFD.IP")

    assert response.status_code == 200
    payload = response.json()["report"]
    assert payload["status"] == "OPERATIONAL"
    assert payload["can_open_new_trade"] is True


def test_safety_register_trade_endpoint_activates_grace_period() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/safety/register-trade",
        json={"epic": "CS.D.EURUSD.CFD.IP", "cooldown_seconds": 60},
    )

    assert response.status_code == 200
    payload = response.json()["report"]
    assert payload["grace_period_active"] is True
    assert payload["can_open_new_trade"] is False
