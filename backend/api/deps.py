"""
FastAPI dependency injection.

Provides:
- get_current_user: extracts user_id from Clerk JWT (or dev fallback)
- get_pipeline: returns singleton PipelineService
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from backend.utils.logger import logger
from backend.config.settings import get_settings

_pipeline_service = None


def get_current_user(authorization: str = Header(None)) -> str:
    """Extract user_id from Authorization header (Clerk JWT or dev bypass)."""
    settings = get_settings()

    if settings.CLERK_DISABLE_AUTH:
        logger.info("Authentication bypassed (CLERK_DISABLE_AUTH=True)")
        return "dev-user"

    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("Invalid Authorization format: {}", authorization[:15])
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Expected: Bearer <token>")

    if not settings.CLERK_JWKS_URL:
        raise HTTPException(status_code=500, detail="CLERK_JWKS_URL not configured")

    try:
        from backend.auth.clerk import verify_clerk_token
        payload = verify_clerk_token(parts[1], settings.CLERK_JWKS_URL)
        user_id = payload.get("sub")
        if not user_id:
            logger.error("Token missing 'sub' claim")
            raise HTTPException(status_code=401, detail="Token missing 'sub' claim")
        
        logger.debug("User authenticated | user_id={}", user_id)
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("JWT verification failed: {}", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_pipeline():
    """Return singleton PipelineService with all V2 services injected."""
    global _pipeline_service

    if _pipeline_service is None:
        settings = get_settings()

        from backend.services.search import SearchService
        from backend.services.debate import DebateService
        from backend.services.judge import JudgeService
        from backend.services.history import HistoryService
        from backend.services.pipeline import PipelineService
        from backend.services.claim import ClaimService
        from backend.services.evidence import EvidenceService
        from backend.services.rounds import RoundsService

        _pipeline_service = PipelineService(
            search=SearchService(tavily_key=settings.TAVILY_API_KEY, serper_key=settings.SERPER_API_KEY),
            debate=DebateService(api_key=settings.GROQ_API_KEY),
            judge=JudgeService(api_key=settings.GROQ_API_KEY),
            history=HistoryService(history_dir=settings.history_dir),
            claim_service=ClaimService(api_key=settings.GROQ_API_KEY),
            evidence_service=EvidenceService(api_key=settings.GROQ_API_KEY),
            rounds_service=RoundsService(api_key=settings.GROQ_API_KEY),
        )

    return _pipeline_service


CurrentUser = Annotated[str, Depends(get_current_user)]
Pipeline = Annotated["PipelineService", Depends(get_pipeline)]
