from fastapi.testclient import TestClient

from positions.application.service import get_positions_service
from safety.application.service import get_safety_service
from src.main import app


def setup_function() -> None:
    get_positions_service().reset()
    get_safety_service().reset()


def test_portfolio_positions_endpoint_returns_paper_snapshot() -> None:
    client = TestClient(app)
    client.post(
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

    response = client.get("/api/v1/portfolio/positions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "paper"
    assert len(payload["local_positions"]) == 1
    assert len(payload["provider_positions"]) == 1


def test_portfolio_reconcile_endpoint_returns_clean_report() -> None:
    client = TestClient(app)
    client.post(
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

    response = client.get("/api/v1/portfolio/reconcile")

    assert response.status_code == 200
    payload = response.json()["report"]
    assert payload["matched_positions"] == 1
    assert payload["discrepancies"] == []
