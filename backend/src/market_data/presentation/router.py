from typing import Annotated

from fastapi import APIRouter, Depends, Query

from market_data.application.dto import CandlesResponse, CandleQuery, Resolution
from market_data.application.service import MarketDataService, get_market_data_service

router = APIRouter(prefix="/market-data", tags=["market-data"])

MarketDataServiceDep = Annotated[MarketDataService, Depends(get_market_data_service)]


@router.get("/{epic}/candles", response_model=CandlesResponse, summary="Get historical candles by epic")
async def get_candles(
    epic: str,
    service: MarketDataServiceDep,
    resolution: Resolution = Query(default="MINUTE"),
    max: int = Query(default=200, ge=1, le=1000),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
) -> CandlesResponse:
    query = CandleQuery(resolution=resolution, max=max, from_=from_, to=to)
    return await service.get_candles(epic, query)
