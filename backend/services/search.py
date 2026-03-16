"""
SearchService — web evidence retrieval.

Fetches results from Tavily (primary) and Serper (supplementary).
Supports per-question search with API call budgeting.
"""

from typing import Optional

import requests

from backend.utils.logger import logger
from backend.core.constants import TRUSTED_SOURCES, MAX_SEARCH_RESULTS
from backend.schemas.internal import SearchResult, SearchContext


class SearchService:
    """Retrieves and merges evidence from Tavily and optionally Serper."""

    def __init__(self, tavily_key: str, serper_key: str = "") -> None:
        self._tavily_key = tavily_key
        self._serper_key = serper_key
        self._session = requests.Session()
        self._calls_used: int = 0
        self._last_tavily_answer: str = ""

    # ── Public API ──────────────────────────────────────────────

    def search(self, query: str) -> SearchContext:
        """
        Execute evidence search: trusted-first, broad fallback, optional Serper.

        Returns deduplicated, score-sorted SearchContext capped at MAX_SEARCH_RESULTS.
        """
        tavily_query = f"Verify this claim with evidence: {query}. Prefer primary, peer-reviewed, or official sources."

        # Trusted-domain search (with one retry before broad fallback)
        primary = self._tavily_search(query=tavily_query, include_domains=TRUSTED_SOURCES, max_results=10)
        self._calls_used = 1

        # If results are weak (fewer than 3 OR low avg relevance) try one quick retry
        avg_score = self._avg_score(primary)
        if len(primary) < 3 or avg_score < 0.8:
            logger.info("Trusted search weak ({} results, avg={:.2f}) — retrying once before broad fallback", len(primary), avg_score)
            retry = self._tavily_search(query=tavily_query, include_domains=TRUSTED_SOURCES, max_results=10)
            self._calls_used += 1
            if retry:
                primary = self._merge_results(primary, retry)
                avg_score = self._avg_score(primary)

        # Broad fallback if still weak and not enough sources (do NOT fallback if we already have >=3 sources)
        if len(primary) < 3 or avg_score < 0.8:
            logger.info("Trusted search still weak ({} results, avg={:.2f}) → broad fallback", len(primary), avg_score)
            broad_query = f"Verify this claim with evidence: {query}. Include all relevant public sources and official reports."
            fallback = self._tavily_search(query=broad_query, max_results=10)
            primary = self._merge_results(primary, fallback)
            self._calls_used += 1

        # Serper supplement
        if self._serper_key:
            serper_results = self._serper_search(query)
            primary = self._merge_results(primary, serper_results)
            self._calls_used += 1

        primary.sort(key=lambda r: r.score, reverse=True)
        capped = primary[:MAX_SEARCH_RESULTS]

        return SearchContext(results=capped, answer=self._last_tavily_answer or "")

    def search_questions(
        self,
        questions: list[str],
        existing_context: SearchContext,
    ) -> SearchContext:
        """Search per verification question and merge into existing context."""
        from backend.core.constants import MAX_SEARCH_CALLS, MAX_CONTEXT

        merged = list(existing_context.results)
        remaining_budget = MAX_SEARCH_CALLS - self._calls_used

        for q in questions[:remaining_budget]:
            logger.debug("Per-question search: {}", q[:80])
            results = self._tavily_search(query=q, max_results=5)
            merged = self._merge_results(merged, results)

        merged.sort(key=lambda r: r.score, reverse=True)
        return SearchContext(results=merged[:MAX_CONTEXT], answer=existing_context.answer)

    # ── Tavily ──────────────────────────────────────────────────

    def _tavily_search(
        self,
        query: str,
        include_domains: Optional[list[str]] = None,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """Call Tavily search API (raw HTTP, no SDK)."""
        payload = {
            "query": query,
            "topic": "news",
            "search_depth": "advanced",
            "max_results": max_results,
            "include_domains": include_domains or [],
            "exclude_domains": [],
            "include_answer": True,
            "include_raw_content": False,
        }
        headers = {
            "Authorization": f"Bearer {self._tavily_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = self._session.post(
                "https://api.tavily.com/search",
                json=payload, headers=headers, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Tavily search failed: {}", e)
            return []

        self._last_tavily_answer = data.get("answer", "")

        return [
            SearchResult(
                title=r.get("title", "Untitled"),
                url=r.get("url", "#"),
                score=round(r.get("score", 0), 2) if isinstance(r.get("score", 0), (int, float)) else 0.0,
                snippet=self._truncate(r.get("content") or r.get("snippet") or "", 300),
            )
            for r in data.get("results", [])
        ]

    # ── Serper ──────────────────────────────────────────────────

    def _serper_search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Call Serper API for supplementary Google results."""
        payload = {"q": query, "num": max_results}
        headers = {"X-API-KEY": self._serper_key, "Content-Type": "application/json"}

        try:
            resp = self._session.post(
                "https://google.serper.dev/search",
                json=payload, headers=headers, timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("Serper search failed (non-critical): {}", e)
            return []

        return [
            SearchResult(
                title=r.get("title", "Untitled"),
                url=r.get("link", "#"),
                score=0.35,
                snippet=self._truncate(r.get("snippet", ""), 300),
            )
            for r in data.get("organic", [])
        ]

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _merge_results(primary: list[SearchResult], secondary: list[SearchResult]) -> list[SearchResult]:
        """Merge two result lists, deduplicating by URL."""
        seen = {r.url for r in primary}
        merged = list(primary)
        for r in secondary:
            if r.url not in seen:
                merged.append(r)
                seen.add(r.url)
        return merged

    @staticmethod
    def _avg_score(results: list[SearchResult]) -> float:
        scores = [r.score for r in results if r.score > 0]
        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        return text if len(text) <= max_len else text[:max_len] + "..."
