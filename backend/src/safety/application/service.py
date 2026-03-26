from datetime import datetime, timedelta, timezone

from authentication.application.service import AuthService, get_auth_service
from execution.domain.models import ExecutionMode
from portfolio.application.dto import PortfolioQuery
from portfolio.application.service import PortfolioService, get_portfolio_service
from safety.application.dto import RegisterTradeRequest, SafetyQuery
from safety.domain.models import SafetyCheck, SafetyReport, SafetyStatus
from shared.config.settings import Settings, get_settings
from shared.errors.base import NotAuthenticatedError


class SafetyService:
    def __init__(self, settings: Settings, auth_service: AuthService, portfolio_service: PortfolioService) -> None:
        self._settings = settings
        self._auth_service = auth_service
        self._portfolio_service = portfolio_service
        self._last_trade_at: datetime | None = None
        self._cooldowns: dict[str, datetime] = {}
        self._grace_period_seconds = 15

    async def evaluate(self, query: SafetyQuery) -> SafetyReport:
        now = datetime.now(timezone.utc)
        self._prune_cooldowns(now)

        checks: list[SafetyCheck] = []

        auth_status = self._auth_service.get_status()
        requires_broker_session = self._resolve_mode(query.execution_mode) == ExecutionMode.IG
        live_config_ok = True
        live_config_detail = "Live IG trading policy allows execution"
        if requires_broker_session and self._settings.ig_environment != "live":
            live_config_ok = False
            live_config_detail = "IG execution requires the backend to run in the live IG environment"
        elif requires_broker_session and not self._settings.allow_live_trading:
            live_config_ok = False
            live_config_detail = "Live IG trading is blocked by configuration"
        checks.append(
            SafetyCheck(
                name="live_trading_configuration",
                passed=live_config_ok,
                detail=live_config_detail,
            )
        )

        auth_ok = True if not requires_broker_session else auth_status.authenticated
        checks.append(
            SafetyCheck(
                name="authenticated_session",
                passed=auth_ok,
                detail="Authenticated IG session available" if auth_ok else "IG execution requires an authenticated session",
            )
        )

        grace_active = self.in_grace_period(now)
        checks.append(
            SafetyCheck(
                name="grace_period",
                passed=not grace_active,
                detail="No grace period active" if not grace_active else "Grace period active after recent trade",
            )
        )

        epic = query.epic
        cooldown_active = epic in self._cooldowns if epic else False
        checks.append(
            SafetyCheck(
                name="epic_cooldown",
                passed=not cooldown_active,
                detail="Epic not in cooldown" if not cooldown_active else f"{epic} is in cooldown",
            )
        )

        try:
            report = await self._portfolio_service.reconcile(PortfolioQuery(execution_mode=query.execution_mode))
            no_ghost_positions = len(report.report.discrepancies) == 0
            reconciliation_detail = (
                "No portfolio discrepancies detected"
                if no_ghost_positions
                else f"Detected {len(report.report.discrepancies)} portfolio discrepancies"
            )
        except NotAuthenticatedError:
            no_ghost_positions = not requires_broker_session
            reconciliation_detail = (
                "Broker reconciliation requires an authenticated session"
                if requires_broker_session
                else "No portfolio discrepancies detected"
            )
        checks.append(
            SafetyCheck(
                name="portfolio_reconciliation",
                passed=no_ghost_positions,
                detail=reconciliation_detail,
            )
        )

        can_open = all(check.passed for check in checks)
        status = SafetyStatus.OPERATIONAL if can_open else SafetyStatus.BLOCKED
        if not can_open and not auth_ok:
            status = SafetyStatus.HIBERNATING

        return SafetyReport(
            status=status,
            can_open_new_trade=can_open,
            checks=checks,
            grace_period_active=grace_active,
            cooldown_epics=sorted(self._cooldowns.keys()),
        )

    def register_trade_execution(self, request: RegisterTradeRequest) -> None:
        now = datetime.now(timezone.utc)
        self._last_trade_at = now
        self._cooldowns[request.epic] = now + timedelta(seconds=request.cooldown_seconds)

    def reset(self) -> None:
        self._last_trade_at = None
        self._cooldowns.clear()

    def in_grace_period(self, now: datetime | None = None) -> bool:
        if self._last_trade_at is None:
            return False
        current = now or datetime.now(timezone.utc)
        return current < self._last_trade_at + timedelta(seconds=self._grace_period_seconds)

    def _prune_cooldowns(self, now: datetime) -> None:
        expired = [epic for epic, until in self._cooldowns.items() if now >= until]
        for epic in expired:
            self._cooldowns.pop(epic, None)

    def _resolve_mode(self, mode: ExecutionMode | None) -> ExecutionMode:
        if mode is not None:
            return mode
        return ExecutionMode.IG if self._settings.execution_mode.lower() == ExecutionMode.IG.value else ExecutionMode.PAPER


_safety_service = SafetyService(get_settings(), get_auth_service(), get_portfolio_service())


def get_safety_service() -> SafetyService:
    return _safety_service
