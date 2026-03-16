"""
ConsistencyService — debate argument quality check.

Measures how consistent arguments are across debate rounds.
"""

from backend.utils.logger import logger
from backend.schemas.internal import MultiRoundDebate


class ConsistencyService:
    """Measures consistency between pro and anti arguments across rounds."""

    @staticmethod
    def check_consistency(debate: MultiRoundDebate) -> float:
        """
        Compute consistency score based on argument quality and evolution.

        Returns 0.0–1.0. Heuristic-based for V2; future: LLM-based analysis.
        """
        if not debate.rounds:
            return 0.5

        rounds = debate.rounds
        score = 0.7  # Base score for having debate content

        # Check both sides have substance
        total_pro = sum(len(r.pro_argument.split()) for r in rounds)
        total_anti = sum(len(r.anti_argument.split()) for r in rounds)

        if total_pro < 20 or total_anti < 20:
            logger.debug("Thin arguments ({} pro words, {} anti words)", total_pro, total_anti)
            return 0.3

        # Multi-round bonus with cross-round coherence check
        if len(rounds) >= 2:
            score += 0.1
            r1_pro = set(rounds[0].pro_argument.lower().split())
            r2_pro = set(rounds[1].pro_argument.lower().split())
            r1_anti = set(rounds[0].anti_argument.lower().split())
            r2_anti = set(rounds[1].anti_argument.lower().split())

            pro_overlap = len(r1_pro & r2_pro) / max(len(r1_pro), 1)
            anti_overlap = len(r1_anti & r2_anti) / max(len(r1_anti), 1)

            # Good overlap range: consistent but not repetitive
            if 0.2 <= pro_overlap <= 0.7:
                score += 0.05
            if 0.2 <= anti_overlap <= 0.7:
                score += 0.05

        return round(min(score, 1.0), 3)
