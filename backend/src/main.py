from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import get_settings
from shared.errors.base import ApplicationError
from shared.logging.setup import configure_logging
from shared.presentation.api import api_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_name, settings.debug)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    @app.exception_handler(ApplicationError)
    async def handle_application_error(_, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
