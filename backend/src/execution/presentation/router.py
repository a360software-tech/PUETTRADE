from fastapi import APIRouter, Depends

from execution.application.dto import CloseExecutionRequest, CloseExecutionResponse, ExecutionResponse, ExecuteLiveRequest, ExecuteSignalRequest
from execution.application.service import ExecutionService, get_execution_service

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/open-position", response_model=ExecutionResponse, summary="Execute validated position from signal")
async def execute_signal(
    request: ExecuteSignalRequest,
    service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    return await service.execute_from_signal(request)


@router.post("/{epic}/open-live-position", response_model=ExecutionResponse, summary="Execute validated live position")
async def execute_live_signal(
    epic: str,
    request: ExecuteLiveRequest,
    service: ExecutionService = Depends(get_execution_service),
) -> ExecutionResponse:
    return await service.execute_live(epic, request)


@router.post("/{position_id}/close", response_model=CloseExecutionResponse, summary="Close executed position")
async def close_execution_position(
    position_id: str,
    request: CloseExecutionRequest,
    service: ExecutionService = Depends(get_execution_service),
) -> CloseExecutionResponse:
    return await service.close_position(position_id, request)
