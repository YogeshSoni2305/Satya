"""
/history endpoint — user verification history.
"""

from fastapi import APIRouter

from backend.utils.logger import logger
from backend.api.deps import CurrentUser
from backend.config.settings import get_settings
from backend.services.history import HistoryService
from backend.schemas.responses import HistoryEntry

router = APIRouter()


@router.get("/history", response_model=list[HistoryEntry])
async def get_history(user_id: CurrentUser) -> list[HistoryEntry]:
    """Return the authenticated user's verification history."""
    logger.info("History called | user_id={}", user_id)
    settings = get_settings()
    return HistoryService(history_dir=settings.history_dir).get(user_id)
