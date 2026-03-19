from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from positions.application.dto import CreatePositionFromSignalRequest, OpenLivePositionRequest
from positions.domain.models import Position, PositionStatus
from shared.errors.base import ApplicationError
from shared.infrastructure.persistence import SQLitePersistence, get_persistence
from strategy.application.service import StrategyService, get_strategy_service


class PositionsService:
    def __init__(self, strategy_service: StrategyService, persistence: SQLitePersistence | None = None) -> None:
        self._strategy_service = strategy_service
        self._persistence = persistence or get_persistence()
        self._positions: dict[str, Position] = {
            position.id: position for position in _load_persisted_positions(self._persistence)
        }
        self._lock = Lock()

    def list_positions(self, status: PositionStatus | None = None) -> list[Position]:
        with self._lock:
            positions = list(self._positions.values())
        if status is None:
            return positions
        return [position for position in positions if position.status == status]

    def get_position(self, position_id: str) -> Position:
        with self._lock:
            position = self._positions.get(position_id)
        if position is None:
            raise ApplicationError("Position not found", status_code=404)
        return position

    def open_from_signal(self, request: CreatePositionFromSignalRequest) -> Position:
        with self._lock:
            self._ensure_no_open_position_for_epic(request.epic)
            position = Position(
                id=str(uuid4()),
                epic=request.epic,
                side=request.signal.side.value,
                entry_price=request.signal.price,
                size=None if request.risk_plan is None else request.risk_plan.size,
                stop_loss=None if request.risk_plan is None else request.risk_plan.stop_loss,
                take_profit=None if request.risk_plan is None else request.risk_plan.take_profit,
                execution_mode=request.execution_mode,
                execution_provider=request.execution_provider,
                provider_deal_id=request.provider_deal_id,
                provider_deal_reference=request.provider_deal_reference,
                opened_at=request.signal.time,
                status=PositionStatus.OPEN,
                signal=request.signal,
            )
            self._positions[position.id] = position
            _persist_position(self._persistence, position)
            return position

    def open_live(self, epic: str, request: OpenLivePositionRequest) -> Position:
        evaluation = self._strategy_service.evaluate_live(
            epic=epic,
            resolution=request.resolution,
            limit=request.limit,
            manifest=request.manifest,
        )
        if evaluation.signal is None:
            detail = evaluation.detail or "Live strategy did not generate a signal"
            raise ApplicationError(detail, status_code=409)

        return self.open_from_signal(
            CreatePositionFromSignalRequest(
                epic=epic,
                signal=evaluation.signal,
            )
        )

    def close_position(self, position_id: str, close_price: float, closed_at: str) -> Position:
        with self._lock:
            position = self._positions.get(position_id)
            if position is None:
                raise ApplicationError("Position not found", status_code=404)
            if position.status == PositionStatus.CLOSED:
                raise ApplicationError("Position is already closed", status_code=409)

            pnl_points = _calculate_pnl_points(position.side, position.entry_price, close_price)
            updated = position.model_copy(
                update={
                    "status": PositionStatus.CLOSED,
                    "close_price": close_price,
                    "closed_at": closed_at,
                    "pnl_points": pnl_points,
                }
            )
            self._positions[position.id] = updated
            _persist_position(self._persistence, updated)
            return updated

    def reset(self) -> None:
        with self._lock:
            self._positions.clear()
            self._persistence.clear_positions()

    def _ensure_no_open_position_for_epic(self, epic: str) -> None:
        for position in self._positions.values():
            if position.epic == epic and position.status == PositionStatus.OPEN:
                raise ApplicationError(f"There is already an open position for {epic}", status_code=409)


def _calculate_pnl_points(side: str, entry_price: float, close_price: float) -> float:
    if side == "LONG":
        return close_price - entry_price
    return entry_price - close_price


def _persist_position(persistence: SQLitePersistence, position: Position) -> None:
    persistence.save_position(
        position_id=position.id,
        payload=position.model_dump(mode="json"),
        status=position.status.value,
        epic=position.epic,
        execution_mode=position.execution_mode,
    )


def _load_persisted_positions(persistence: SQLitePersistence) -> list[Position]:
    return [Position.model_validate(payload) for payload in persistence.load_positions()]


_positions_service = PositionsService(get_strategy_service())


def get_positions_service() -> PositionsService:
    return _positions_service


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
