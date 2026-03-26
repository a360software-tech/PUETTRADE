import asyncio

import pytest

from authentication.application.service import AuthService
from execution.domain.models import ExecutionMode
from execution.application.service import ExecutionService
from positions.application.service import get_positions_service
from risk.application.service import get_risk_service
from safety.application.dto import SafetyQuery
from safety.application.service import SafetyService
from shared.config.settings import Settings
from shared.errors.base import ApplicationError


class _AuthStub:
    def get_status(self):
        class _Status:
            authenticated = False

        return _Status()

    def get_access_token(self) -> str:
        return ""

    async def get_session_tokens(self):
        raise RuntimeError("unused")

    async def is_session_alive(self):
        class _Health:
            alive = False
            detail = "No active session"

        return _Health()


class _PortfolioStub:
    async def reconcile(self, query):
        class _Report:
            discrepancies = []

        class _Response:
            report = _Report()

        return _Response()


class _MarketDiscoveryStub:
    async def get_market_status(self, epic: str) -> str:
        return "TRADEABLE"


def test_settings_reject_live_environment_with_demo_urls() -> None:
    with pytest.raises(ValueError):
        Settings(
            IG_ENVIRONMENT="live",
            IG_API_URL="https://demo-api.ig.com/gateway/deal",
            IG_LIGHTSTREAMER_URL="https://demo-apd.marketdatasystems.com",
        )


def test_auth_service_rejects_account_type_mismatch() -> None:
    service = AuthService(Settings(IG_ENVIRONMENT="demo"))

    with pytest.raises(ApplicationError, match="configured for IG demo accounts only"):
        service._validate_requested_account_type("live")


def test_auth_service_reports_session_health_without_active_session() -> None:
    service = AuthService(Settings(IG_ENVIRONMENT="demo"))

    health = asyncio.run(service.is_session_alive())

    assert health.alive is False
    assert health.detail == "No active session"


def test_execution_service_blocks_ig_execution_when_live_trading_disabled() -> None:
    settings = Settings(
        IG_ENVIRONMENT="live",
        ALLOW_LIVE_TRADING=False,
        IG_API_URL="https://api.ig.com/gateway/deal",
        IG_LIGHTSTREAMER_URL="https://apd.marketdatasystems.com",
    )
    service = ExecutionService(settings, get_risk_service(), get_positions_service(), _AuthStub())

    with pytest.raises(ApplicationError, match="Live IG trading is blocked by configuration"):
        service._resolve_gateway(explicit_mode=None, fallback_mode="ig")


def test_safety_blocks_ig_execution_when_backend_is_not_live() -> None:
    service = SafetyService(Settings(IG_ENVIRONMENT="demo"), _AuthStub(), _PortfolioStub(), _MarketDiscoveryStub())

    report = asyncio.run(
        service.evaluate(SafetyQuery(epic="CS.D.EURUSD.CFD.IP", execution_mode=ExecutionMode.IG))
    )

    assert report.can_open_new_trade is False
    assert any(check.name == "live_trading_configuration" and not check.passed for check in report.checks)
