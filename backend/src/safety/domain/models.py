from enum import Enum

from pydantic import BaseModel


class SafetyStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    HIBERNATING = "HIBERNATING"
    BLOCKED = "BLOCKED"


class SafetyCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class SafetyReport(BaseModel):
    status: SafetyStatus
    can_open_new_trade: bool
    checks: list[SafetyCheck]
    grace_period_active: bool
    cooldown_epics: list[str]
