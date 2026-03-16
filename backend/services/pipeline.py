"""
PipelineService — V2 courtroom verification orchestrator.

13-step flow: normalize → search → questions → search/question → rank →
extract evidence → debate (2 rounds) → contradiction → consistency →
judge verdict → hybrid confidence → save history → return
"""

from backend.utils.logger import logger
from backend.services.search import SearchService
from backend.services.claim import ClaimService
from backend.services.evidence import EvidenceService
from backend.services.reliability import ReliabilityService
from backend.services.rounds import RoundsService
from backend.services.contradiction import ContradictionService
from backend.services.consistency import ConsistencyService
from backend.services.judge import JudgeService
from backend.services.scoring import ScoringService
from backend.services.history import HistoryService
from backend.schemas.responses import (
    VerifyResponse, Source, DebatePosition, HistoryEntry,
)


class PipelineService:
    """Orchestrates the full V2 accuracy pipeline."""

    def __init__(
        self,
        search: SearchService,
        debate: object,
        judge: JudgeService,
        history: HistoryService,
        claim_service: ClaimService | None = None,
        evidence_service: EvidenceService | None = None,
        rounds_service: RoundsService | None = None,
    ) -> None:
        self._search = search
        self._judge = judge
        self._history = history
        self._claim = claim_service
        self._evidence = evidence_service
        self._rounds = rounds_service

    def run(self, text: str, user_id: str, request_id: str = "-") -> VerifyResponse:
        """Execute the full 13-step verification pipeline."""
        log = logger.bind(request_id=request_id)
        log.info("Pipeline started | user={}", user_id)

        # Step 1: Normalize claim
        if self._claim:
            normalized = self._claim.normalize(text)
            claim_text = normalized.claim
        else:
            claim_text = text
            normalized = None

        # Step 2: Initial search (with one retry on failure/empty)
        log.info("Search started")
        try:
            context = self._search.search(claim_text)
            # If search returned no results, try one more time
            if not context.results:
                log.warning("Initial search returned no results, retrying once")
                context = self._search.search(claim_text)
        except Exception as e:
            log.error("Search raised exception: {} | continuing with empty context", e)
            from backend.schemas.internal import SearchContext
            context = SearchContext(results=[], answer="")

        log.info("Search finished | {} results", len(context.results))

        # Step 3: Generate verification questions
        questions = self._judge.generate_questions(claim_text, context)
        log.info("Generated {} questions", len(questions))

        # Step 4: Per-question search + merge
        log.info("Search started | per-question searches")
        try:
            context = self._search.search_questions(questions, context)
        except Exception as e:
            log.warning("Per-question search failed: {} | continuing with existing context", e)
        log.info("Search finished | per-question merge complete | {} results", len(context.results))

        # Step 5: Rank sources by reliability
        context = ReliabilityService.score_context(context)
        log.info("Source reliability avg: {:.2f}", context.avg_reliability)

        # Step 6: Extract evidence
        log.info("Evidence started")
        if self._evidence and normalized:
            evidence = self._evidence.extract(normalized, context)
        else:
            from backend.schemas.internal import EvidenceContext, EvidenceItem
            items = [
                EvidenceItem(text=r.snippet[:150], source_url=r.url, source_title=r.title)
                for r in context.results[:6]
            ]
            evidence = EvidenceContext(items=items)
        log.info("Evidence finished | {} items", len(evidence.items))

        # Step 7: Multi-round debate
        log.info("Debate started")
        if self._rounds:
            multi_debate = self._rounds.run_debate(claim_text, questions, context, evidence)
        else:
            from backend.schemas.internal import DebateRound, MultiRoundDebate
            multi_debate = MultiRoundDebate(rounds=[DebateRound(claim=claim_text)])

        # Step 8: Contradiction detection
        agreement_score = ContradictionService.check_contradictions(evidence)

        # Step 9: Consistency check
        consistency_score = ConsistencyService.check_consistency(multi_debate)

        # Step 10: Judge verdict
        log.info("Judge started")
        verdict = self._judge.verdict(
            claim=claim_text, debate=multi_debate,
            evidence=evidence, context=context, agreement_score=agreement_score,
        )
        log.info("LLM verdict: {} (confidence={:.2f})", verdict.verdict, verdict.confidence)

        # Step 11: Hybrid confidence
        hybrid_confidence = ScoringService.compute(
            llm_verdict=verdict, context=context, evidence=evidence,
            agreement_score=agreement_score, consistency_score=consistency_score,
        )
        log.info("Scoring finished | confidence={:.3f}", hybrid_confidence)

        # Build response
        sources = [
            Source(title=r.title, url=r.url, score=r.score, snippet=r.snippet)
            for r in context.results
        ]
        debate_positions = []
        for rnd in multi_debate.rounds:
            debate_positions.append(DebatePosition(role="pro", argument=f"[Round {rnd.round_number}] {rnd.pro_argument}"))
            debate_positions.append(DebatePosition(role="anti", argument=f"[Round {rnd.round_number}] {rnd.anti_argument}"))

        response = VerifyResponse(
            claim=claim_text, verdict=verdict.verdict,
            confidence=hybrid_confidence, conclusion=verdict.conclusion,
            evidence_summary=verdict.evidence_summary,
            sources=sources, debate=debate_positions, questions=questions,
            agreement_score=agreement_score, evidence_strength=verdict.evidence_strength,
            source_reliability=context.avg_reliability,
            evidence_count=len(evidence.items), consistency_score=consistency_score,
        )

        # Step 12: Save history
        entry = HistoryEntry(
            claim=claim_text, verdict=verdict.verdict,
            confidence=hybrid_confidence, sources=sources[:3],
        )
        self._history.save(user_id, entry)

        log.info("Pipeline complete | verdict={} | confidence={:.3f}", verdict.verdict, hybrid_confidence)
        return response
