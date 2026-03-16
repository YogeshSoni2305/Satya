"""
ReliabilityService — source domain scoring.

Scores search results by their domain's reliability tier
using the DOMAIN_RELIABILITY lookup table.
"""

from urllib.parse import urlparse

from backend.core.constants import DOMAIN_RELIABILITY, DEFAULT_DOMAIN_SCORE
from backend.schemas.internal import SearchResult, SearchContext


class ReliabilityService:
    """Scores and ranks search results by source reliability."""

    @staticmethod
    def score_source(url: str) -> float:
        """Return reliability score for a URL's domain (checks subdomains)."""
        try:
            domain = urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            return DEFAULT_DOMAIN_SCORE

        parts = domain.split(".")
        for i in range(len(parts) - 1):
            candidate = ".".join(parts[i:])
            if candidate in DOMAIN_RELIABILITY:
                return DOMAIN_RELIABILITY[candidate]

        return DEFAULT_DOMAIN_SCORE

    @classmethod
    def score_context(cls, context: SearchContext) -> SearchContext:
        """Add reliability scores to all results and re-sort by reliability then relevance."""
        scored = [
            SearchResult(
                title=r.title, url=r.url, score=r.score,
                snippet=r.snippet, reliability=cls.score_source(r.url),
            )
            for r in context.results
        ]
        scored.sort(key=lambda x: (x.reliability, x.score), reverse=True)
        return SearchContext(results=scored, answer=context.answer)
