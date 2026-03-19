from fastapi import APIRouter

from engine.presentation.router import router as engine_router
from execution.presentation.router import router as execution_router
from authentication.presentation.router import router as authentication_router
from market_data.presentation.router import router as market_data_router
from market_data.presentation.stream import router as market_data_stream_router
from market_discovery.presentation.router import router as market_discovery_router
from portfolio.presentation.router import router as portfolio_router
from positions.presentation.router import router as positions_router
from risk.presentation.router import router as risk_router
from safety.presentation.router import router as safety_router
from strategy.presentation.router import router as strategy_router

api_router = APIRouter()

api_router.include_router(engine_router)
api_router.include_router(execution_router)
api_router.include_router(authentication_router)
api_router.include_router(market_data_router)
api_router.include_router(market_data_stream_router)
api_router.include_router(market_discovery_router)
api_router.include_router(portfolio_router)
api_router.include_router(positions_router)
api_router.include_router(risk_router)
api_router.include_router(safety_router)
api_router.include_router(strategy_router)


@api_router.get("/system/architecture", tags=["system"])
async def architecture_overview() -> dict[str, object]:
    return {
        "style": "screaming architecture",
        "provider": "IG Labs",
        "bounded_contexts": [
            "authentication",
            "engine",
            "execution",
            "market_data",
            "market_discovery",
            "portfolio",
            "positions",
            "risk",
            "safety",
            "strategy",
        ],
    }
