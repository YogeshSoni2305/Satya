# """
# FastAPI application factory.

# Creates the app, registers routers, configures CORS.
# Uses loguru instead of stdlib logging.
# """

# import sys
# from contextlib import asynccontextmanager

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from backend.utils.logger import logger
# from backend.config.settings import get_settings


# # Intercept stdlib logging → loguru (for uvicorn and third-party libs)
# import logging
# origins = settings.cors_origin_list

# class _InterceptHandler(logging.Handler):
#     """Route stdlib logging records to loguru."""

#     def emit(self, record: logging.LogRecord) -> None:
#         try:
#             level = logger.level(record.levelname).name
#         except ValueError:
#             level = record.levelno
#         logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


# logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
# for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
#     logging.getLogger(name).handlers = [_InterceptHandler()]


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Startup and shutdown lifecycle."""
#     settings = get_settings()
#     logger.info("Starting Satya API")
#     logger.info("CORS origins: {}", settings.cors_origin_list)
#     logger.info("Auth disabled: {}", settings.CLERK_DISABLE_AUTH)
#     logger.info("Serper configured: {}", bool(settings.SERPER_API_KEY))

#     # Pre-initialize pipeline
#     from backend.api.deps import get_pipeline
#     get_pipeline()
#     logger.info("Pipeline service initialized")

#     yield

#     logger.info("Shutting down Satya API")


# def create_app() -> FastAPI:
#     """Create and configure the FastAPI application."""
#     settings = get_settings()

#     app = FastAPI(
#         title="Satya API",
#         description="Courtroom-style AI fact-checking API",
#         version="2.0.0",
#         lifespan=lifespan,
#     )

#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=origins,
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

#     from backend.api.routes import verify, history, health
#     app.include_router(verify.router, tags=["Verification"])
#     app.include_router(history.router, tags=["History"])
#     app.include_router(health.router, tags=["Health"])

#     return app


# app = create_app()
















import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.utils.logger import logger
from backend.config.settings import get_settings

import logging


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
    logging.getLogger(name).handlers = [_InterceptHandler()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logger.info("Starting Satya API")
    logger.info("CORS origins: {}", settings.cors_origin_list)
    logger.info("Auth disabled: {}", settings.CLERK_DISABLE_AUTH)
    logger.info("Serper configured: {}", bool(settings.SERPER_API_KEY))

    from backend.api.deps import get_pipeline
    get_pipeline()

    logger.info("Pipeline service initialized")

    yield

    logger.info("Shutting down Satya API")


def create_app() -> FastAPI:
    settings = get_settings()

    origins = settings.cors_origin_list  # ✅ move here

    app = FastAPI(
        title="Satya API",
        description="Courtroom-style AI fact-checking API",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.api.routes import verify, history, health

    app.include_router(verify.router, tags=["Verification"])
    app.include_router(history.router, tags=["History"])
    app.include_router(health.router, tags=["Health"])

    return app


app = create_app()