from fastapi import APIRouter, Depends, Query

from positions.application.dto import (
    ClosePositionRequest,
    CreatePositionFromSignalRequest,
    OpenLivePositionRequest,
    PositionListResponse,
    PositionResponse,
)
from positions.application.service import PositionsService, get_positions_service
from positions.domain.models import PositionStatus

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=PositionListResponse, summary="List positions")
async def list_positions(
    status: PositionStatus | None = Query(default=None),
    service: PositionsService = Depends(get_positions_service),
) -> PositionListResponse:
    return PositionListResponse(items=service.list_positions(status=status))


@router.get("/{position_id}", response_model=PositionResponse, summary="Get position by id")
async def get_position(
    position_id: str,
    service: PositionsService = Depends(get_positions_service),
) -> PositionResponse:
    return PositionResponse(position=service.get_position(position_id))


@router.post("/from-signal", response_model=PositionResponse, summary="Open position from strategy signal")
async def open_position_from_signal(
    request: CreatePositionFromSignalRequest,
    service: PositionsService = Depends(get_positions_service),
) -> PositionResponse:
    return PositionResponse(position=service.open_from_signal(request))


@router.post("/{epic}/open-live", response_model=PositionResponse, summary="Open position from live strategy signal")
async def open_live_position(
    epic: str,
    request: OpenLivePositionRequest,
    service: PositionsService = Depends(get_positions_service),
) -> PositionResponse:
    return PositionResponse(position=service.open_live(epic, request))


@router.post("/{position_id}/close", response_model=PositionResponse, summary="Close position")
async def close_position(
    position_id: str,
    request: ClosePositionRequest,
    service: PositionsService = Depends(get_positions_service),
) -> PositionResponse:
    return PositionResponse(position=service.close_position(position_id, request.close_price, request.closed_at))
