from typing import Annotated

from fastapi import APIRouter, Depends

from authentication.application.dto import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SessionStatusResponse,
    StreamingTokensResponse,
)
from authentication.application.service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/login", response_model=LoginResponse, summary="Login to IG Trading")
async def login(
    request: LoginRequest,
    service: AuthServiceDep,
) -> LoginResponse:
    return await service.login(request)


@router.post("/logout", summary="Logout from IG Trading")
async def logout(service: AuthServiceDep) -> dict[str, str]:
    await service.logout()
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=RefreshResponse, summary="Refresh access token")
async def refresh(
    request: RefreshRequest,
    service: AuthServiceDep,
) -> RefreshResponse:
    return await service.refresh(request)


@router.get("/session", response_model=StreamingTokensResponse, summary="Get streaming session tokens")
async def get_session_tokens(
    service: AuthServiceDep,
) -> StreamingTokensResponse:
    return await service.get_session_tokens()


@router.get("/status", response_model=SessionStatusResponse, summary="Get current session status")
async def get_status(service: AuthServiceDep) -> SessionStatusResponse:
    return service.get_status()
