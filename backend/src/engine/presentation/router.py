from fastapi import APIRouter, Depends

from engine.application.dto import EngineCycleResponse, EngineRunCycleRequest, EngineStartRequest, EngineStatusResponse
from engine.application.service import EngineService, get_engine_service

router = APIRouter(prefix="/engine", tags=["engine"])


@router.get("/status", response_model=EngineStatusResponse, summary="Get engine status")
async def get_engine_status(
    service: EngineService = Depends(get_engine_service),
) -> EngineStatusResponse:
    return service.get_status()


@router.post("/start", response_model=EngineStatusResponse, summary="Start engine")
async def start_engine(
    request: EngineStartRequest,
    service: EngineService = Depends(get_engine_service),
) -> EngineStatusResponse:
    return service.start(request)


@router.post("/stop", response_model=EngineStatusResponse, summary="Stop engine")
async def stop_engine(
    service: EngineService = Depends(get_engine_service),
) -> EngineStatusResponse:
    return service.stop()


@router.post("/pause", response_model=EngineStatusResponse, summary="Pause engine")
async def pause_engine(
    service: EngineService = Depends(get_engine_service),
) -> EngineStatusResponse:
    return service.pause()


@router.post("/run-cycle", response_model=EngineCycleResponse, summary="Run a single engine cycle")
async def run_engine_cycle(
    request: EngineRunCycleRequest,
    service: EngineService = Depends(get_engine_service),
) -> EngineCycleResponse:
    return await service.run_cycle(request)
