"""
Internal pipeline types — not exposed to API consumers.
"""

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single search result from Tavily or Serper."""
    title: str = "Untitled"
    url: str = "#"
    score: float = 0.0
    snippet: str = ""
    reliability: float = 0.0  # V2: domain reliability score


class SearchContext(BaseModel):
    """Aggregated search evidence for a claim."""
    results: list[SearchResult] = []
    answer: str = ""  # Tavily's AI-generated answer summary

    @property
    def formatted(self) -> str:
        """Render search context as a text block for LLM consumption."""
        if not self.results:
            return "No evidence found."
        lines = []
        for i, r in enumerate(self.results, 1):
            rel = f" [reliability: {r.reliability:.2f}]" if r.reliability > 0 else ""
            lines.append(f"[{i}] {r.title} ({r.url}){rel}\n    {r.snippet}")
        if self.answer:
            lines.insert(0, f"Summary: {self.answer}\n")
        return "\n".join(lines)

    @property
    def avg_reliability(self) -> float:
        """Average reliability score of all sources."""
        scores = [r.reliability for r in self.results if r.reliability > 0]
        return sum(scores) / len(scores) if scores else 0.0


class NormalizedClaim(BaseModel):
    """V2: Normalized claim output from ClaimService."""
    claim: str = ""
    entities: list[str] = []
    time_reference: str = ""
    topic: str = ""
    original_text: str = ""


class EvidenceItem(BaseModel):
    """V2: A single extracted evidence sentence."""
    text: str
    source_url: str = ""
    source_title: str = ""
    relevance: str = "medium"  # high / medium / low
    supports_claim: str = "neutral"  # supports / contradicts / neutral


class EvidenceContext(BaseModel):
    """V2: Structured evidence extracted from search results."""
    items: list[EvidenceItem] = []
    supporting_count: int = 0
    contradicting_count: int = 0
    neutral_count: int = 0

    @property
    def formatted(self) -> str:
        """Render evidence as a text block for LLM consumption."""
        if not self.items:
            return "No evidence extracted."
        lines = []
        for i, e in enumerate(self.items, 1):
            stance = f"[{e.supports_claim.upper()}]"
            lines.append(f"[E{i}] {stance} {e.text}\n      Source: {e.source_title} ({e.source_url})")
        return "\n".join(lines)


class DebateRound(BaseModel):
    """The full courtroom exchange for a single claim."""
    claim: str
    questions: list[str] = []
    pro_argument: str = ""
    anti_argument: str = ""
    round_number: int = 1  # V2: round tracking


class MultiRoundDebate(BaseModel):
    """V2: Contains all rounds of debate."""
    rounds: list[DebateRound] = []

    @property
    def formatted(self) -> str:
        """Render all debate rounds for the judge."""
        lines = []
        for r in self.rounds:
            lines.append(f"--- Round {r.round_number} ---")
            lines.append(f"PRO: {r.pro_argument}")
            lines.append(f"ANTI: {r.anti_argument}")
            lines.append("")
        return "\n".join(lines)


class JudgeVerdict(BaseModel):
    """Schema for the judge LLM's JSON output (V2: expanded)."""
    verdict: str = Field(..., description="True | False | Unverifiable")
    confidence: float = Field(..., ge=0.0, le=1.0)
    conclusion: str = Field(..., description="Short paragraph (<=50 words)")
    evidence_summary: str = Field(..., description="Key evidence or gap (<=30 words)")
    agreement_score: float = Field(0.5, ge=0.0, le=1.0, description="How much evidence agrees")
    evidence_strength: str = Field("medium", description="strong / medium / weak / none")
    source_reliability: float = Field(0.5, ge=0.0, le=1.0, description="Avg source reliability")

