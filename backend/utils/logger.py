"""
Centralized logging setup using loguru.

Replaces stdlib logging with structured loguru logger.
Supports request_id binding for per-request tracing.

Usage:
    from backend.utils.logger import logger

    # In pipeline/services — bind request_id for tracing
    log = logger.bind(request_id="abc-123")
    log.info("Processing claim")

    # In modules without request context
    logger.info("Server starting")
"""

import sys
import uuid

from loguru import logger as _loguru_logger

# Remove default loguru handler (stderr with colors)
_loguru_logger.remove()

# ── Console handler ───────────────────────────────────────────
_loguru_logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[request_id]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    ),
    level="INFO",
    filter=lambda record: record["extra"].setdefault("request_id", "-"),
    colorize=True,
    backtrace=False,
    diagnose=False,
)

# Export configured logger
logger = _loguru_logger


def generate_request_id() -> str:
    """Generate a short unique request ID for tracing."""
    return uuid.uuid4().hex[:12]
