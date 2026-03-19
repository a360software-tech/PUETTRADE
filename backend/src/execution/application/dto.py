from pydantic import BaseModel

from positions.application.dto import ClosePositionRequest
from positions.domain.models import Position
from risk.application.dto import EvaluateLiveRiskRequest, EvaluateRiskRequest
from risk.domain.models import RiskDecision

from execution.domain.models import ExecutionMode, ExecutionRecord


class ExecuteSignalRequest(EvaluateRiskRequest):
    execution_mode: ExecutionMode | None = None


class ExecuteLiveRequest(EvaluateLiveRiskRequest):
    execution_mode: ExecutionMode | None = None


class ExecutionResponse(BaseModel):
    epic: str
    decision: RiskDecision
    execution: ExecutionRecord
    position: Position


class CloseExecutionRequest(ClosePositionRequest):
    execution_mode: ExecutionMode | None = None


class CloseExecutionResponse(BaseModel):
    position: Position
    execution: ExecutionRecord
