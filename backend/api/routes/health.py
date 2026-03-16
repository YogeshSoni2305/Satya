"""
/health endpoint — simple health check.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": "satya-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
