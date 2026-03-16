"""
ContradictionService — evidence agreement analysis.

Computes how much the evidence agrees or contradicts itself.
"""

from backend.utils.logger import logger
from backend.schemas.internal import EvidenceContext


class ContradictionService:
    """Detects contradictions within the evidence set."""

    @staticmethod
    def check_contradictions(evidence: EvidenceContext) -> float:
        """
        Compute agreement score from evidence distribution.

        Returns 0.0–1.0: 1.0 = full agreement, 0.0 = equal split, 0.5 = no directional evidence.
        """
        s, c = evidence.supporting_count, evidence.contradicting_count
        total = s + c

        if total == 0:
            return 0.5

        agreement = round(abs(s - c) / total, 3)
        logger.debug("Agreement score: {:.2f} (supporting={}, contradicting={})", agreement, s, c)
        return agreement
