from fastapi.testclient import TestClient

from src.main import app


def test_healthcheck() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cors_allows_frontend_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/api/v1/system/architecture",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_auth_status_defaults_to_unauthenticated() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/auth/status")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "account_id": None, "account_type": None, "lightstreamer_endpoint": None}


def test_architecture_only_exposes_active_contexts() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/system/architecture")

    assert response.status_code == 200
    assert response.json()["bounded_contexts"] == ["authentication", "market_data", "market_discovery"]


def test_market_data_requires_authenticated_session() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/market-data/CS.D.EURUSD.CFD.IP/candles")

    assert response.status_code == 401
    assert response.json() == {"detail": "No active session"}
