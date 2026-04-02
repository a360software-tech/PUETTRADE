from positions.domain.models import Position
from shared.infrastructure.persistence import DatabasePersistence, get_persistence


class PositionRepository:
    def __init__(self, persistence: DatabasePersistence | None = None) -> None:
        self._persistence = persistence or get_persistence()

    def list(self) -> list[Position]:
        return [Position.model_validate(payload) for payload in self._persistence.load_positions()]

    def save(self, position: Position) -> None:
        self._persistence.save_position(
            position_id=position.id,
            payload=position.model_dump(mode="json"),
            status=position.status.value,
            epic=position.epic,
            execution_mode=position.execution_mode,
        )

    def clear(self) -> None:
        self._persistence.clear_positions()


def get_position_repository() -> PositionRepository:
    return PositionRepository()
