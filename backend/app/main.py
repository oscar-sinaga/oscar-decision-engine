"""FastAPI application factory for OSCAR Decision Engine."""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.shared.config import get_settings
from app.shared.domain.error_handlers import register_error_handlers
from app.shared.logging import configure_logging
from app.shared.logging.middleware import CorrelationMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)

    app = FastAPI(
        title="OSCAR Decision Engine",
        version="0.1.0",
        description=(
            "Internal credit-risk decision engine: configurable rules and strategies, "
            "immutable decision traces, simulation, manual review, and audit."
        ),
    )
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
