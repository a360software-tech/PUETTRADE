from authentication.application.service import AuthService, get_auth_service
from execution.application.dto import (
    CloseExecutionRequest,
    CloseExecutionResponse,
    ExecutionResponse,
    ExecuteLiveRequest,
    ExecuteSignalRequest,
)
from execution.infrastructure.repository import ExecutionEventRepository, get_execution_event_repository
from execution.application.ports import ExecutionPort
from execution.domain.models import ExecutionMode, ExecutionRecord, ExecutionStatus
from integrations.ig.rest.trading_client import IgTradingClient
from positions.application.dto import CreatePositionFromSignalRequest
from positions.application.service import PositionsService, get_positions_service
from positions.domain.models import Position
from risk.application.service import RiskService, get_risk_service
from safety.application.dto import RegisterTradeRequest, SafetyQuery
from safety.application.service import SafetyService, get_safety_service
from shared.application.notifier import EventNotifier
from shared.config.settings import Settings, get_settings
from shared.domain.events import ExecutionRecordedEvent, ExecutionRejectedEvent
from shared.errors.base import ApplicationError


execution_event_notifier = EventNotifier[ExecutionRecordedEvent]()
execution_rejection_notifier = EventNotifier[ExecutionRejectedEvent]()


class PaperExecutionGateway(ExecutionPort):
    def __init__(self, positions_service: PositionsService) -> None:
        self._positions_service = positions_service

    async def open_position(self, *, epic: str, decision) -> tuple[ExecutionRecord, Position]:
        if decision.signal is None or decision.plan is None:
            raise ApplicationError("Cannot execute without approved signal and risk plan", status_code=409)

        execution_context = _build_execution_context(decision=decision, execution_mode=ExecutionMode.PAPER.value, execution_provider="paper")
        position = self._positions_service.open_from_signal(
            CreatePositionFromSignalRequest(
                epic=epic,
                signal=decision.signal,
                risk_plan=decision.plan,
                execution_mode=ExecutionMode.PAPER.value,
                execution_provider="paper",
                execution_context=execution_context,
            )
        )
        return (
            ExecutionRecord(
                mode=ExecutionMode.PAPER,
                provider="paper",
                status=ExecutionStatus.FILLED,
                reason="Paper execution filled locally",
            ),
            position,
        )

    async def close_position(self, *, position: Position, request: CloseExecutionRequest) -> tuple[ExecutionRecord, Position]:
        closed = self._positions_service.close_position(position.id, request.close_price, request.closed_at)
        return (
            ExecutionRecord(
                mode=ExecutionMode.PAPER,
                provider="paper",
                status=ExecutionStatus.FILLED,
                reason="Paper position closed locally",
            ),
            closed,
        )


class IgExecutionGateway(ExecutionPort):
    def __init__(self, settings: Settings, auth_service: AuthService, positions_service: PositionsService) -> None:
        self._client = IgTradingClient(settings)
        self._auth_service = auth_service
        self._positions_service = positions_service

    async def open_position(self, *, epic: str, decision) -> tuple[ExecutionRecord, Position]:
        if decision.signal is None or decision.plan is None:
            raise ApplicationError("Cannot execute without approved signal and risk plan", status_code=409)

        access_token = self._auth_service.get_access_token()
        tokens = await self._auth_service.get_session_tokens()
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "CST": tokens.cst,
            "X-SECURITY-TOKEN": tokens.x_security_token,
            "IG-ACCOUNT-ID": tokens.account_id,
            "Version": "2",
        }
        direction = "BUY" if decision.signal.side.value == "LONG" else "SELL"

        response = await self._client.open_market_position(
            epic=epic,
            direction=direction,
            size=decision.plan.size,
            auth_headers=auth_headers,
            stop_level=decision.plan.stop_loss,
            limit_level=decision.plan.take_profit,
        )
        deal_reference = _as_optional_str(response.get("dealReference"))
        confirmation = response
        deal_id = _as_optional_str(response.get("dealId"))
        if deal_reference:
            confirmation = await self._client.confirm_deal(deal_reference, auth_headers=auth_headers)
            deal_id = _as_optional_str(confirmation.get("dealId")) or deal_id
            if str(confirmation.get("dealStatus", "ACCEPTED")).upper() != "ACCEPTED":
                raise ApplicationError(str(confirmation.get("reason", "IG execution rejected")), status_code=409)

        execution_context = _build_execution_context(decision=decision, execution_mode=ExecutionMode.IG.value, execution_provider="ig")
        position = self._positions_service.open_from_signal(
            CreatePositionFromSignalRequest(
                epic=epic,
                signal=decision.signal,
                risk_plan=decision.plan,
                execution_mode=ExecutionMode.IG.value,
                execution_provider="ig",
                provider_deal_id=deal_id,
                provider_deal_reference=deal_reference,
                execution_context=execution_context,
            )
        )
        return (
            ExecutionRecord(
                mode=ExecutionMode.IG,
                provider="ig",
                status=ExecutionStatus.FILLED,
                reason="IG execution accepted",
                deal_reference=deal_reference,
                deal_id=deal_id,
            ),
            position,
        )

    async def close_position(self, *, position: Position, request: CloseExecutionRequest) -> tuple[ExecutionRecord, Position]:
        if not position.provider_deal_id:
            raise ApplicationError("Position does not have an IG deal id", status_code=409)

        access_token = self._auth_service.get_access_token()
        tokens = await self._auth_service.get_session_tokens()
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "CST": tokens.cst,
            "X-SECURITY-TOKEN": tokens.x_security_token,
            "IG-ACCOUNT-ID": tokens.account_id,
            "Version": "1",
        }
        direction = "SELL" if position.side == "LONG" else "BUY"
        size = position.size or 0.0
        response = await self._client.close_position(
            deal_id=position.provider_deal_id,
            direction=direction,
            size=size,
            auth_headers=auth_headers,
        )
        deal_reference = _as_optional_str(response.get("dealReference"))
        confirmation = response
        if deal_reference:
            confirmation = await self._client.confirm_deal(deal_reference, auth_headers=auth_headers)
            if str(confirmation.get("dealStatus", "ACCEPTED")).upper() != "ACCEPTED":
                raise ApplicationError(str(confirmation.get("reason", "IG close rejected")), status_code=409)

        closed = self._positions_service.close_position(position.id, request.close_price, request.closed_at)
        return (
            ExecutionRecord(
                mode=ExecutionMode.IG,
                provider="ig",
                status=ExecutionStatus.FILLED,
                reason="IG close accepted",
                deal_reference=deal_reference,
                deal_id=position.provider_deal_id,
            ),
            closed,
        )


class ExecutionService:
    def __init__(
        self,
        settings: Settings,
        risk_service: RiskService,
        safety_service: SafetyService,
        positions_service: PositionsService,
        auth_service: AuthService,
        repository: ExecutionEventRepository | None = None,
        notifier: EventNotifier[ExecutionRecordedEvent] | None = None,
    ) -> None:
        self._settings = settings
        self._risk_service = risk_service
        self._safety_service = safety_service
        self._positions_service = positions_service
        self._repository = repository or get_execution_event_repository()
        self._notifier = notifier or execution_event_notifier
        self._paper_gateway = PaperExecutionGateway(positions_service)
        self._ig_gateway = IgExecutionGateway(settings, auth_service, positions_service)

    async def process_signal(self, request: ExecuteSignalRequest) -> ExecutionResponse:
        return await self.execute_from_signal(request)

    async def process_live_signal(self, epic: str, request: ExecuteLiveRequest) -> ExecutionResponse:
        return await self.execute_live(epic, request)

    async def execute_from_signal(self, request: ExecuteSignalRequest) -> ExecutionResponse:
        await self._ensure_can_execute(epic=request.epic, execution_mode=request.execution_mode, action="open_signal")
        evaluation = self._risk_service.evaluate_signal(request)
        decision = evaluation.decision
        if not decision.approved or decision.signal is None or decision.plan is None:
            self._notify_rejection(request.epic, "open_signal", decision.reason, decision)
            raise ApplicationError(decision.reason, status_code=409)

        gateway = self._resolve_gateway(request.execution_mode)
        _validate_signal_price(decision.signal.price)
        execution, position = await gateway.open_position(epic=request.epic, decision=decision)
        self._safety_service.register_trade_execution(RegisterTradeRequest(epic=request.epic))
        self._record_execution_event(request.epic, position.id, execution, "open_signal", decision.reason)
        return ExecutionResponse(epic=request.epic, decision=decision, execution=execution, position=position)

    async def execute_live(self, epic: str, request: ExecuteLiveRequest) -> ExecutionResponse:
        await self._ensure_can_execute(epic=epic, execution_mode=request.execution_mode, action="open_live")
        evaluation = self.evaluate_live_decision(epic, request)
        decision = evaluation.decision
        if not decision.approved or decision.signal is None or decision.plan is None:
            self._notify_rejection(epic, "open_live", decision.reason, decision)
            raise ApplicationError(decision.reason, status_code=409)

        gateway = self._resolve_gateway(request.execution_mode)
        _validate_signal_price(decision.signal.price)
        execution, position = await gateway.open_position(epic=epic, decision=decision)
        self._safety_service.register_trade_execution(RegisterTradeRequest(epic=epic))
        self._record_execution_event(epic, position.id, execution, "open_live", decision.reason)
        return ExecutionResponse(epic=epic, decision=decision, execution=execution, position=position)

    def evaluate_live_decision(self, epic: str, request: ExecuteLiveRequest):
        return self._risk_service.evaluate_live(epic, request)

    async def close_position(self, position_id: str, request: CloseExecutionRequest) -> CloseExecutionResponse:
        position = self._positions_service.get_position(position_id)
        gateway = self._resolve_gateway(request.execution_mode, position.execution_mode)
        execution, closed = await gateway.close_position(position=position, request=request)
        self._record_execution_event(position.epic, closed.id, execution, "close_position", execution.reason)
        return CloseExecutionResponse(position=closed, execution=execution)

    def _resolve_gateway(
        self,
        explicit_mode: ExecutionMode | None,
        fallback_mode: str | None = None,
    ) -> ExecutionPort:
        requested = explicit_mode.value if explicit_mode is not None else fallback_mode or self._settings.execution_mode
        mode = requested.lower()
        if mode == ExecutionMode.IG.value:
            if self._settings.ig_environment != "live":
                raise ApplicationError(
                    "IG execution requires the backend to run in the live IG environment",
                    status_code=409,
                )
            if not self._settings.allow_live_trading:
                raise ApplicationError("Live IG trading is blocked by configuration", status_code=409)
            return self._ig_gateway
        return self._paper_gateway

    async def _ensure_can_execute(self, *, epic: str, execution_mode: ExecutionMode | None, action: str) -> None:
        report = await self._safety_service.evaluate(SafetyQuery(epic=epic, execution_mode=execution_mode))
        if report.can_open_new_trade:
            return

        reason = "; ".join(check.detail for check in report.checks if not check.passed)
        self._notify_rejection(epic, action, reason, decision=None)
        raise ApplicationError(reason, status_code=409)

    def _record_execution_event(
        self,
        epic: str,
        position_id: str,
        execution: ExecutionRecord,
        event_type: str,
        detail: str,
    ) -> None:
        self._repository.append(
            epic=epic,
            position_id=position_id,
            execution=execution,
            event_type=event_type,
            detail=detail,
        )
        position = self._positions_service.get_position(position_id)
        self._notifier.notify(
            ExecutionRecordedEvent(
                epic=epic,
                position=position,
                execution=execution,
                action=event_type,
            )
        )

    def _notify_rejection(self, epic: str, action: str, reason: str, decision) -> None:
        execution_rejection_notifier.notify(
            ExecutionRejectedEvent(
                epic=epic,
                reason=reason,
                action=action,
                decision=decision,
            )
        )


def get_execution_service() -> ExecutionService:
    return ExecutionService(get_settings(), get_risk_service(), get_safety_service(), get_positions_service(), get_auth_service())


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_signal_price(price: float) -> None:
    if price <= 0:
        raise ApplicationError("Signal price must be greater than zero", status_code=409)


def _build_execution_context(*, decision, execution_mode: str, execution_provider: str) -> dict[str, object]:
    signal = decision.signal
    plan = decision.plan
    return {
        "decision_reason": decision.reason,
        "signal_reason": None if signal is None else signal.reason,
        "signal_phase": None if signal is None else signal.phase,
        "signal_momentum": None if signal is None else signal.momentum,
        "risk_plan": None if plan is None else plan.model_dump(mode="json"),
        "execution_mode": execution_mode,
        "execution_provider": execution_provider,
    }
