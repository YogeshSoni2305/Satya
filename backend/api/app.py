"""
FastAPI application factory.

Creates the app, registers routers, and configures CORS.
Uses loguru for unified logging across the application.
"""

import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.utils.logger import logger
from backend.config.settings import get_settings


class _InterceptHandler(logging.Handler):
    """Route stdlib logging records to loguru for consistent formatting."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


# Intercept stdlib logging (uvicorn, fastapi) and redirect to loguru
logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
    logging.getLogger(name).handlers = [_InterceptHandler()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle handler.
    Logs configuration status for debugging deployment issues.
    """
    settings = get_settings()
    logger.info("🚀 Starting Satya API")
    
    # Debug logs for CORS origins (critical for Render + Vercel troubleshooting)
    logger.info("CORS configuration: allowed_origins={}", settings.cors_origin_list)
    logger.info("Authentication: CLERK_DISABLE_AUTH={}", settings.CLERK_DISABLE_AUTH)
    logger.info("Search Service: Serper configured={}", bool(settings.SERPER_API_KEY))

    # Pre-initialize pipeline for faster first request
    from backend.api.deps import get_pipeline
    get_pipeline()
    logger.info("✅ Pipeline service initialized")

    yield

    logger.info("🛑 Shutting down Satya API")


def create_app() -> FastAPI:
    """Create, configure, and return the FastAPI application instance."""
    settings = get_settings()
    
    app = FastAPI(
        title="Satya API",
        description="Courtroom-style AI fact-checking API",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Apply CORS middleware BEFORE including any routers
    # Note: allow_credentials MUST be True if using Auth headers/cookies
    origins = settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("Middleware: CORS applied with origins={}", origins)

    # Import and register routers
    from backend.api.routes import verify, history, health
    app.include_router(verify.router, prefix="", tags=["Verification"])
    app.include_router(history.router, prefix="", tags=["History"])
    app.include_router(health.router, prefix="", tags=["Health"])

    return app


# Application global instance
app = create_app()