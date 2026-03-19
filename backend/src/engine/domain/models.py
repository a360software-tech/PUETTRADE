from enum import Enum

from pydantic import BaseModel


class EngineMode(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class EngineEpicState(BaseModel):
    epic: str
    resolution: str
    limit: int
    last_signal_time: str | None = None
    last_position_id: str | None = None
    last_decision_reason: str | None = None
    last_run_at: str | None = None
    last_error: str | None = None
