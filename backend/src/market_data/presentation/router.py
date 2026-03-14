from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.security import OAuth2PasswordBearer

from market_data.application.dto import CandleQuery, CandlesResponse, Resolution
from market_data.application.service import MarketDataService, get_market_data_service
from authentication.application.service import AuthService, get_auth_service
from authentication.application.dto import StreamingTokensResponse

router = APIRouter(prefix="/market-data", tags=["market-data"])

MarketDataServiceDep = Annotated[MarketDataService, Depends(get_market_data_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


@router.get("/{epic}/candles", response_model=CandlesResponse, summary="Get historical candles by epic")
async def get_candles(
    epic: str,
    token: str | None = Depends(oauth2_scheme),
    service: MarketDataServiceDep = MarketDataServiceDep,
    auth_service: AuthServiceDep = AuthServiceDep,
    resolution: Resolution = Query(default="MINUTE"),
    max: int = Query(default=200, ge=1, le=1000),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
) -> CandlesResponse:
    query = CandleQuery(resolution=resolution, max=max, from_=from_, to=to)
    return await service.get_candles(epic, query, token, auth_service)
