from pydantic import BaseModel, Field

from execution.domain.models import ExecutionMode
from safety.domain.models import SafetyReport


class SafetyQuery(BaseModel):
    epic: str | None = None
    execution_mode: ExecutionMode | None = None


class RegisterTradeRequest(BaseModel):
    epic: str
    cooldown_seconds: int = Field(default=60, ge=1, le=3600)


class SafetyResponse(BaseModel):
    report: SafetyReport
