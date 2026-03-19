from enum import Enum

from pydantic import BaseModel


class ExecutionMode(str, Enum):
    PAPER = "paper"
    IG = "ig"


class ExecutionStatus(str, Enum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"


class ExecutionRecord(BaseModel):
    mode: ExecutionMode
    provider: str
    status: ExecutionStatus
    reason: str
    deal_reference: str | None = None
    deal_id: str | None = None
