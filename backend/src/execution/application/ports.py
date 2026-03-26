from typing import Protocol

from execution.application.dto import CloseExecutionRequest
from execution.domain.models import ExecutionRecord
from positions.domain.models import Position


class ExecutionPort(Protocol):
    async def open_position(
        self,
        *,
        epic: str,
        decision,
    ) -> tuple[ExecutionRecord, Position]:
        ...

    async def close_position(
        self,
        *,
        position: Position,
        request: CloseExecutionRequest,
    ) -> tuple[ExecutionRecord, Position]:
        ...
