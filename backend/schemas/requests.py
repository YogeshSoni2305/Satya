"""
Request schemas for the API layer.
"""

from pydantic import BaseModel, Field

from backend.core.constants import MIN_CLAIM_LENGTH, MAX_CLAIM_LENGTH


class VerifyRequest(BaseModel):
    """Input payload for the /verify endpoint."""
    text: str = Field(
        ...,
        min_length=MIN_CLAIM_LENGTH,
        max_length=MAX_CLAIM_LENGTH,
        description="The text claim to fact-check",
        examples=["The Earth is flat and NASA has confirmed this."],
    )
