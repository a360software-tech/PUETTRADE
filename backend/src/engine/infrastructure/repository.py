from engine.domain.models import EngineEpicState
from shared.infrastructure.persistence import DatabasePersistence, get_persistence


class EngineStateRepository:
    def __init__(self, persistence: DatabasePersistence | None = None) -> None:
        self._persistence = persistence or get_persistence()

    def load(self) -> tuple[str, list[EngineEpicState]]:
        mode, states = self._persistence.load_engine_state()
        return mode, [EngineEpicState.model_validate(payload) for payload in states]

    def save_mode(self, mode: str) -> None:
        self._persistence.save_engine_mode(mode)

    def save_epic_state(self, state: EngineEpicState) -> None:
        self._persistence.save_engine_epic(state.epic, state.model_dump(mode="json"))

    def clear(self) -> None:
        self._persistence.clear_engine_state()


def get_engine_state_repository() -> EngineStateRepository:
    return EngineStateRepository()
