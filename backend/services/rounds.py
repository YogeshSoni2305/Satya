"""
RoundsService — multi-round debate orchestration.

Runs 2 rounds: opening arguments then rebuttals.
"""

from backend.utils.logger import logger
from backend.core.llm import GroqClient
from backend.core.constants import MODEL_PRO_LAWYER, MODEL_ANTI_LAWYER, MAX_DEBATE_TOKENS
from backend.schemas.internal import (
    SearchContext, EvidenceContext, DebateRound, MultiRoundDebate,
)


class RoundsService:
    """Runs a 2-round adversarial debate."""

    def __init__(self, api_key: str) -> None:
        from backend.prompts.pro import PRO_LAWYER_PROMPT
        from backend.prompts.anti import ANTI_LAWYER_PROMPT

        self._pro = GroqClient(
            api_key=api_key, model=MODEL_PRO_LAWYER,
            system_prompt=PRO_LAWYER_PROMPT,
            temperature=0.6, max_tokens=MAX_DEBATE_TOKENS, top_p=0.95,
        )
        self._anti = GroqClient(
            api_key=api_key, model=MODEL_ANTI_LAWYER,
            system_prompt=ANTI_LAWYER_PROMPT,
            temperature=0.7, max_tokens=MAX_DEBATE_TOKENS,
        )

    def run_debate(
        self,
        claim: str,
        questions: list[str],
        context: SearchContext,
        evidence: EvidenceContext,
    ) -> MultiRoundDebate:
        """Run 2 rounds: opening arguments then rebuttals."""
        evidence_text = evidence.formatted
        questions_text = "\n".join(f"- {q}" for q in questions) if questions else "No specific questions."

        # Round 1 — Opening arguments
        pro1 = self._safe_pro(
            f"CLAIM: {claim}\n\nEVIDENCE:\n{evidence_text}\n\n"
            f"VERIFICATION QUESTIONS:\n{questions_text}\n\n"
            "Present your opening argument. This claim is TRUE.\n"
            "Use ONLY the evidence provided. Cite evidence by number [E1], [E2], etc.\n"
            "Address each verification question. Max 200 words."
        )

        anti1 = self._safe_anti(
            f"CLAIM: {claim}\n\nEVIDENCE:\n{evidence_text}\n\n"
            f"PRO LAWYER'S ARGUMENT:\n{pro1}\n\n"
            "Critique the pro lawyer's argument. Argue this claim is FALSE or UNVERIFIABLE.\n"
            "Point out weak evidence, logical gaps, and counter-evidence.\n"
            "Cite evidence by number [E1], [E2], etc. Max 150 words."
        )

        round1 = DebateRound(
            claim=claim, questions=questions,
            pro_argument=pro1, anti_argument=anti1, round_number=1,
        )

        # Round 2 — Rebuttals
        pro2 = self._safe_pro(
            f"CLAIM: {claim}\n\nYOUR ROUND 1 ARGUMENT:\n{pro1}\n\n"
            f"ANTI LAWYER'S CRITIQUE:\n{anti1}\n\nEVIDENCE:\n{evidence_text}\n\n"
            "Respond to the anti lawyer's critique. Defend your position.\n"
            "Address their specific objections with evidence. Max 150 words."
        )

        anti2 = self._safe_anti(
            f"CLAIM: {claim}\n\nPRO LAWYER'S REBUTTAL:\n{pro2}\n\n"
            f"YOUR ROUND 1 CRITIQUE:\n{anti1}\n\nEVIDENCE:\n{evidence_text}\n\n"
            "Final response. Strengthen your strongest objection.\n"
            "If the pro lawyer addressed your concerns adequately, acknowledge it.\nMax 100 words."
        )

        round2 = DebateRound(
            claim=claim, questions=questions,
            pro_argument=pro2, anti_argument=anti2, round_number=2,
        )

        return MultiRoundDebate(rounds=[round1, round2])

    def _safe_pro(self, prompt: str) -> str:
        """Call pro lawyer with error handling."""
        try:
            _, result = self._pro.chat_with_thinking(prompt)
            return result
        except Exception as e:
            logger.error("Pro lawyer failed: {}", e)
            return "Unable to formulate argument."

    def _safe_anti(self, prompt: str) -> str:
        """Call anti lawyer with error handling."""
        try:
            return self._anti.chat(prompt)
        except Exception as e:
            logger.error("Anti lawyer failed: {}", e)
            return "Unable to formulate critique."
