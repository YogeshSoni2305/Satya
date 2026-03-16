"""
/verify endpoint — main fact-checking pipeline.
"""

import asyncio

from fastapi import APIRouter

from backend.utils.logger import logger, generate_request_id
from backend.api.deps import CurrentUser, Pipeline
from backend.schemas.requests import VerifyRequest
from backend.schemas.responses import VerifyResponse

router = APIRouter()


@router.post("/verify", response_model=VerifyResponse)
async def verify_claim(
    request: VerifyRequest,
    user_id: CurrentUser,
    pipeline: Pipeline,
) -> VerifyResponse:
    """Fact-check a text claim through the courtroom pipeline."""
    request_id = generate_request_id()
    log = logger.bind(request_id=request_id)
    log.info("Verify called | user_id={} | text='{}'", user_id, request.text[:60])

    # Run synchronous pipeline in thread pool
    result = await asyncio.to_thread(pipeline.run, request.text, user_id, request_id)

    log.info("Verify complete | verdict={}", result.verdict)
    return result
