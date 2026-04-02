from execution.application.dto import ExecuteLiveRequest
from execution.application.service import ExecutionService, get_execution_service
from datetime import datetime, timezone
from threading import RLock

from engine.application.dto import EngineCycleResponse, EngineRunCycleRequest, EngineStartRequest, EngineStatusResponse
from engine.domain.models import EngineEpicState, EngineMode
from engine.infrastructure.repository import EngineStateRepository, get_engine_state_repository
from safety.application.dto import RegisterTradeRequest, SafetyQuery
from safety.application.service import SafetyService, get_safety_service
from shared.errors.base import ApplicationError


class EngineService:
    def __init__(
        self,
        execution_service: ExecutionService,
        safety_service: SafetyService,
        repository: EngineStateRepository | None = None,
    ) -> None:
        self._execution_service = execution_service
        self._safety_service = safety_service
        self._repository = repository or get_engine_state_repository()
        mode, states = self._repository.load()
        self._mode = EngineMode(mode)
        self._epics: dict[str, EngineEpicState] = {state.epic: state for state in states}
        self._lock = RLock()

    def get_status(self) -> EngineStatusResponse:
        with self._lock:
            tracked = [state.model_copy(deep=True) for state in self._epics.values()]
            active_epics = list(self._epics.keys())
            mode = self._mode
        return EngineStatusResponse(mode=mode, active_epics=active_epics, tracked=tracked)

    def start(self, request: EngineStartRequest) -> EngineStatusResponse:
        with self._lock:
            self._mode = EngineMode.RUNNING
            self._repository.save_mode(self._mode.value)
            for epic in request.epics:
                state = self._epics.setdefault(epic, _default_state(epic=epic, resolution="MINUTE_5", limit=100))
                self._repository.save_epic_state(state)
        return self.get_status()

    def stop(self) -> EngineStatusResponse:
        with self._lock:
            self._mode = EngineMode.STOPPED
            self._repository.save_mode(self._mode.value)
        return self.get_status()

    def pause(self) -> EngineStatusResponse:
        with self._lock:
            self._mode = EngineMode.PAUSED
            self._repository.save_mode(self._mode.value)
        return self.get_status()

    async def run_cycle(self, request: EngineRunCycleRequest) -> EngineCycleResponse:
        with self._lock:
            if self._mode == EngineMode.STOPPED:
                raise ApplicationError("Engine is stopped. Start it before running cycles.", status_code=409)
            current_state = self._epics.get(request.epic) or _default_state(request.epic, request.resolution, request.limit)
            current_state.resolution = request.resolution
            current_state.limit = request.limit
            self._epics[request.epic] = current_state
            self._repository.save_epic_state(current_state)

        try:
            safety_report = await self._safety_service.evaluate(
                SafetyQuery(epic=request.epic, execution_mode=request.execution_mode)
            )
            if not safety_report.can_open_new_trade:
                reason = "; ".join(check.detail for check in safety_report.checks if not check.passed)
                with self._lock:
                    state = self._epics[request.epic]
                    state.last_run_at = _utc_now_iso()
                    state.last_error = reason
                    state.last_decision_reason = reason
                    self._repository.save_epic_state(state)
                return EngineCycleResponse(
                    epic=request.epic,
                    mode=self._mode,
                    action="blocked_by_safety",
                    state=self._snapshot_state(request.epic),
                    decision=None,
                    execution=None,
                    position_id=None,
                )

            execution_request = ExecuteLiveRequest(
                resolution=request.resolution,
                limit=request.limit,
                manifest=request.manifest,
                settings=request.settings,
                execution_mode=request.execution_mode,
            )
            evaluation = self._execution_service.evaluate_live_decision(request.epic, execution_request)
            decision = evaluation.decision
            now = _utc_now_iso()

            with self._lock:
                state = self._epics[request.epic]
                state.last_run_at = now
                state.last_decision_reason = decision.reason
                state.last_error = None
                self._repository.save_epic_state(state)
                if decision.signal is not None and state.last_signal_time == decision.signal.time:
                    return EngineCycleResponse(
                        epic=request.epic,
                        mode=self._mode,
                        action="duplicate_signal_skipped",
                        state=self._snapshot_state(request.epic),
                        decision=decision,
                        execution=None,
                        position_id=state.last_position_id,
                    )

            if not decision.approved or decision.signal is None or decision.plan is None:
                return EngineCycleResponse(
                    epic=request.epic,
                    mode=self._mode,
                    action="skipped",
                    state=self._snapshot_state(request.epic),
                    decision=decision,
                    execution=None,
                    position_id=None,
                )

            opened = await self._execution_service.execute_live(request.epic, execution_request)

            with self._lock:
                state = self._epics[request.epic]
                state.last_signal_time = opened.position.signal.time
                state.last_position_id = opened.position.id
                state.last_decision_reason = opened.decision.reason
                state.last_run_at = now
                state.last_error = None
                self._repository.save_epic_state(state)
            self._safety_service.register_trade_execution(RegisterTradeRequest(epic=request.epic))

            return EngineCycleResponse(
                epic=request.epic,
                mode=self._mode,
                action="position_opened",
                state=self._snapshot_state(request.epic),
                decision=opened.decision,
                execution=opened.execution,
                position_id=opened.position.id,
            )
        except ApplicationError as exc:
            with self._lock:
                state = self._epics[request.epic]
                state.last_run_at = _utc_now_iso()
                state.last_error = exc.detail
                state.last_decision_reason = exc.detail
                self._repository.save_epic_state(state)
            if "already an open position" in exc.detail:
                return EngineCycleResponse(
                    epic=request.epic,
                    mode=self._mode,
                    action="position_exists",
                    state=self._snapshot_state(request.epic),
                    decision=None,
                    execution=None,
                    position_id=self._snapshot_state(request.epic).last_position_id,
                )
            raise

    def reset(self) -> None:
        with self._lock:
            self._mode = EngineMode.STOPPED
            self._epics.clear()
            self._repository.clear()

    def _snapshot_state(self, epic: str) -> EngineEpicState:
        with self._lock:
            state = self._epics[epic]
            return state.model_copy(deep=True)


def _default_state(epic: str, resolution: str, limit: int) -> EngineEpicState:
    return EngineEpicState(epic=epic, resolution=resolution, limit=limit)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_engine_service = EngineService(get_execution_service(), get_safety_service())


def get_engine_service() -> EngineService:
    return _engine_service
