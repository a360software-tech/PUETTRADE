from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)
    account_type: Literal["demo", "live"] = "demo"


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    account_id: str
    account_type: str
    lightstreamer_endpoint: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class SessionStatusResponse(BaseModel):
    authenticated: bool
    account_id: str | None = None
    account_type: str | None = None
    lightstreamer_endpoint: str | None = None


class StreamingTokensResponse(BaseModel):
    cst: str
    x_security_token: str
    account_id: str
