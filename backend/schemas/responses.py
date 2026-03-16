"""
Response schemas returned by the API.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A single search evidence source."""
    title: str = "Untitled"
    url: str = "#"
    score: float = 0.0
    snippet: str = ""


class DebatePosition(BaseModel):
    """One side of the courtroom debate."""
    role: Literal["pro", "anti"]
    argument: str


class Verdict(BaseModel):
    """The judge's final ruling."""
    verdict: Literal["True", "False", "Unverifiable"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    conclusion: str = Field(..., max_length=500)
    evidence_summary: str = Field(..., max_length=300)


class VerifyResponse(BaseModel):
    """Full response from the /verify endpoint."""
    claim: str
    verdict: str
    confidence: float
    conclusion: str
    evidence_summary: str
    sources: list[Source] = []
    debate: list[DebatePosition] = []
    questions: list[str] = []
    # V2 fields
    agreement_score: float = 0.5
    evidence_strength: str = "medium"
    source_reliability: float = 0.5
    evidence_count: int = 0
    consistency_score: float = 0.5


class HistoryEntry(BaseModel):
    """One entry in a user's verification history."""
    claim: str
    verdict: str
    confidence: float
    sources: list[Source] = []
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
