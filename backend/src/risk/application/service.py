from positions.application.dto import CreatePositionFromSignalRequest
from positions.application.service import PositionsService, get_positions_service
from positions.domain.models import PositionStatus
from risk.application.dto import (
    EvaluateLiveRiskRequest,
    EvaluateRiskRequest,
    RiskEvaluationResponse,
    RiskOpenPositionResponse,
)
from risk.domain.models import RiskDecision, RiskPlan, RiskSettings
from strategy.application.service import StrategyService, get_strategy_service
from strategy.domain.models import SignalSide, StrategySignal


class RiskService:
    def __init__(self, strategy_service: StrategyService, positions_service: PositionsService) -> None:
        self._strategy_service = strategy_service
        self._positions_service = positions_service

    def evaluate_signal(self, request: EvaluateRiskRequest) -> RiskEvaluationResponse:
        decision = self._build_decision(request.epic, request.signal, request.settings)
        return RiskEvaluationResponse(epic=request.epic, decision=decision, source="manual_signal")

    def evaluate_live(self, epic: str, request: EvaluateLiveRiskRequest) -> RiskEvaluationResponse:
        evaluation = self._strategy_service.evaluate_live(
            epic=epic,
            resolution=request.resolution,
            limit=request.limit,
            manifest=request.manifest,
        )
        signal = evaluation.signal
        if signal is None:
            return RiskEvaluationResponse(
                epic=epic,
                decision=RiskDecision(approved=False, reason=evaluation.detail or "No live signal available"),
                source="live_strategy",
            )

        decision = self._build_decision(epic, signal, request.settings)
        return RiskEvaluationResponse(epic=epic, decision=decision, source="live_strategy")

    def open_validated_from_signal(self, request: EvaluateRiskRequest) -> RiskOpenPositionResponse:
        decision = self._build_decision(request.epic, request.signal, request.settings)
        if not decision.approved or decision.plan is None or decision.signal is None:
            raise _risk_rejection(decision.reason)

        position = self._positions_service.open_from_signal(
            CreatePositionFromSignalRequest(epic=request.epic, signal=decision.signal, risk_plan=decision.plan)
        )
        return RiskOpenPositionResponse(
            epic=request.epic,
            decision=decision,
            position=position,
            source="manual_signal",
        )

    def open_validated_live(self, epic: str, request: EvaluateLiveRiskRequest) -> RiskOpenPositionResponse:
        evaluation = self.evaluate_live(epic, request)
        decision = evaluation.decision
        if not decision.approved or decision.plan is None or decision.signal is None:
            raise _risk_rejection(decision.reason)

        position = self._positions_service.open_from_signal(
            CreatePositionFromSignalRequest(epic=epic, signal=decision.signal, risk_plan=decision.plan)
        )
        return RiskOpenPositionResponse(
            epic=epic,
            decision=decision,
            position=position,
            source="live_strategy",
        )

    def _build_decision(self, epic: str, signal: StrategySignal, settings: RiskSettings) -> RiskDecision:
        open_positions = self._positions_service.list_positions(status=PositionStatus.OPEN)
        if len(open_positions) >= settings.max_open_positions:
            return RiskDecision(approved=False, reason="Maximum open positions reached", signal=signal)

        if any(position.epic == epic for position in open_positions):
            return RiskDecision(approved=False, reason=f"There is already an open position for {epic}", signal=signal)

        if signal.price <= 0:
            return RiskDecision(approved=False, reason="Signal price must be greater than zero", signal=signal)

        if not _signal_strength_allows_trade(signal):
            return RiskDecision(approved=False, reason="Signal momentum does not meet risk validation rules", signal=signal)

        plan = _build_plan(signal, settings)
        return RiskDecision(approved=True, reason="Risk approved", signal=signal, plan=plan)


def get_risk_service() -> RiskService:
    return RiskService(get_strategy_service(), get_positions_service())


def _build_plan(signal: StrategySignal, settings: RiskSettings) -> RiskPlan:
    entry_price = signal.price
    stop_distance = entry_price * settings.stop_loss_pct

    if signal.side == SignalSide.LONG:
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + (stop_distance * settings.take_profit_ratio)
    else:
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - (stop_distance * settings.take_profit_ratio)

    capital_at_risk = settings.account_balance * settings.risk_per_trade_pct
    raw_size = capital_at_risk / stop_distance
    max_notional = settings.account_balance * settings.max_position_notional_pct
    max_size_by_notional = max_notional / entry_price
    size = min(raw_size, max_size_by_notional)
    notional_exposure = size * entry_price

    return RiskPlan(
        size=size,
        capital_at_risk=capital_at_risk,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_reward_ratio=settings.take_profit_ratio,
        notional_exposure=notional_exposure,
    )


def _signal_strength_allows_trade(signal: StrategySignal) -> bool:
    if signal.momentum is None:
        return True
    if signal.side == SignalSide.LONG:
        return signal.momentum <= 40
    if signal.side == SignalSide.SHORT:
        return signal.momentum >= 60
    return True


def _risk_rejection(reason: str) -> Exception:
    from shared.errors.base import ApplicationError

    return ApplicationError(reason, status_code=409)
