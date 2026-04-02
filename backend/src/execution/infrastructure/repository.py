from execution.domain.models import ExecutionRecord
from shared.infrastructure.persistence import DatabasePersistence, get_persistence


class ExecutionEventRepository:
    def __init__(self, persistence: DatabasePersistence | None = None) -> None:
        self._persistence = persistence or get_persistence()

    def append(
        self,
        *,
        epic: str,
        position_id: str,
        execution: ExecutionRecord,
        event_type: str,
        detail: str,
    ) -> None:
        self._persistence.append_execution_event(
            epic=epic,
            position_id=position_id,
            execution_mode=execution.mode.value,
            event_type=event_type,
            payload={
                "provider": execution.provider,
                "status": execution.status.value,
                "reason": execution.reason,
                "deal_reference": execution.deal_reference,
                "deal_id": execution.deal_id,
                "detail": detail,
            },
        )


def get_execution_event_repository() -> ExecutionEventRepository:
    return ExecutionEventRepository()
