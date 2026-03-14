from fastapi import APIRouter

from authentication.presentation.router import router as authentication_router
from market_data.presentation.router import router as market_data_router
from market_discovery.presentation.router import router as market_discovery_router

api_router = APIRouter()

api_router.include_router(authentication_router)
api_router.include_router(market_data_router)
api_router.include_router(market_discovery_router)


@api_router.get("/system/architecture", tags=["system"])
async def architecture_overview() -> dict[str, object]:
    return {
        "style": "screaming architecture",
        "provider": "IG Labs",
        "bounded_contexts": [
            "authentication",
            "market_data",
            "market_discovery",
        ],
    }
