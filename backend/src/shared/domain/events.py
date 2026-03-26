from dataclasses import dataclass, field
from datetime import UTC, datetime

from execution.domain.models import ExecutionRecord
from positions.domain.models import Position
from risk.domain.models import RiskDecision


@dataclass(slots=True)
class PositionOpenedEvent:
    position: Position
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class PositionClosedEvent:
    position: Position
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ExecutionRecordedEvent:
    epic: str
    position: Position
    execution: ExecutionRecord
    action: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ExecutionRejectedEvent:
    epic: str
    reason: str
    action: str
    decision: RiskDecision | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
