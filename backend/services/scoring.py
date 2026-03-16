"""
ScoringService — hybrid confidence calculation.

Combines multiple signals into a weighted final confidence score.
"""

from backend.utils.logger import logger
from backend.schemas.internal import JudgeVerdict, SearchContext, EvidenceContext

# Weights for hybrid confidence formula (adjusted to reduce consistency overweight)
W_LLM = 0.25
W_SOURCE = 0.25
W_AGREEMENT = 0.15
W_EVIDENCE = 0.20
W_CONSISTENCY = 0.15


class ScoringService:
    """Computes hybrid confidence from multiple signals."""

    @staticmethod
    def compute(
        llm_verdict: JudgeVerdict,
        context: SearchContext,
        evidence: EvidenceContext,
        agreement_score: float,
        consistency_score: float,
    ) -> float:
        """
        Compute final hybrid confidence score (0.0–1.0).

        Formula: 0.25×LLM + 0.25×source + 0.15×agreement + 0.20×evidence + 0.15×consistency
        """
        source_reliability = context.avg_reliability

        total_evidence = len(evidence.items)
        evidence_ratio = (
            (evidence.supporting_count + evidence.contradicting_count) / total_evidence
            if total_evidence > 0 else 0.0
        )

        final = (
            W_LLM * llm_verdict.confidence
            + W_SOURCE * source_reliability
            + W_AGREEMENT * agreement_score
            + W_EVIDENCE * evidence_ratio
            + W_CONSISTENCY * consistency_score
        )

        final = max(0.0, min(1.0, round(final, 3)))

        logger.info(
            "Hybrid confidence: {:.3f} (llm={:.2f} src={:.2f} agree={:.2f} ev={:.2f} cons={:.2f})",
            final, llm_verdict.confidence, source_reliability,
            agreement_score, evidence_ratio, consistency_score,
        )

        return final
