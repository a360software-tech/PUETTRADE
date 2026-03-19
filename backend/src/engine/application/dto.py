from pydantic import BaseModel, Field

from engine.domain.models import EngineEpicState, EngineMode
from execution.domain.models import ExecutionMode, ExecutionRecord
from risk.application.dto import EvaluateLiveRiskRequest
from risk.domain.models import RiskDecision


class EngineStartRequest(BaseModel):
    epics: list[str] = Field(default_factory=list, max_length=100)


class EngineRunCycleRequest(EvaluateLiveRiskRequest):
    epic: str
    execution_mode: ExecutionMode | None = None


class EngineCycleResponse(BaseModel):
    epic: str
    mode: EngineMode
    action: str
    state: EngineEpicState
    decision: RiskDecision | None = None
    execution: ExecutionRecord | None = None
    position_id: str | None = None


class EngineStatusResponse(BaseModel):
    mode: EngineMode
    active_epics: list[str]
    tracked: list[EngineEpicState]
