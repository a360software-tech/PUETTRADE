from typing import Annotated

from fastapi import APIRouter, Depends, Query

from market_discovery.application.dto import (
    CategoryResponse,
    InstrumentResponse,
    MarketDetailResponse,
    MarketSearchResult,
    WatchlistItemResponse,
)
from market_discovery.application.service import MarketDiscoveryService, get_market_discovery_service

router = APIRouter(prefix="/markets", tags=["market-discovery"])

MarketDiscoveryServiceDep = Annotated[MarketDiscoveryService, Depends(get_market_discovery_service)]


@router.get("/categories", response_model=list[CategoryResponse], summary="Get market categories")
async def get_categories(
    service: MarketDiscoveryServiceDep,
) -> list[CategoryResponse]:
    return await service.get_categories()


@router.get("/watchlist", response_model=list[WatchlistItemResponse], summary="Get default watchlist epics")
async def get_default_watchlist(
    service: MarketDiscoveryServiceDep,
) -> list[WatchlistItemResponse]:
    return await service.get_default_watchlist()


@router.get("/categories/{category_id}/instruments", response_model=list[InstrumentResponse], summary="Get instruments by category")
async def get_instruments(
    category_id: str,
    service: MarketDiscoveryServiceDep,
) -> list[InstrumentResponse]:
    return await service.get_instruments(category_id)


@router.get("/search", response_model=list[MarketSearchResult], summary="Search markets")
async def search_markets(
    service: MarketDiscoveryServiceDep,
    q: str = Query(..., description="Search term"),
) -> list[MarketSearchResult]:
    return await service.search_markets(q)


@router.get("/{epic}", response_model=MarketDetailResponse, summary="Get market detail by epic")
async def get_market_detail(
    epic: str,
    service: MarketDiscoveryServiceDep,
) -> MarketDetailResponse:
    return await service.get_market_detail(epic)
