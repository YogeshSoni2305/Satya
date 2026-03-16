"""
DebateService — courtroom-style adversarial debate.

Pro argues FOR the claim, anti argues AGAINST.
Lawyers receive search context as read-only input — no direct search calls.
"""

from backend.utils.logger import logger
from backend.core.llm import GroqClient
from backend.core.constants import MODEL_PRO_LAWYER, MODEL_ANTI_LAWYER
from backend.schemas.internal import SearchContext, DebateRound


class DebateService:
    """Runs one round of adversarial debate between pro and anti lawyers."""

    def __init__(self, api_key: str) -> None:
        from backend.prompts.pro import PRO_LAWYER_PROMPT
        from backend.prompts.anti import ANTI_LAWYER_PROMPT

        self._pro = GroqClient(
            api_key=api_key,
            model=MODEL_PRO_LAWYER,
            system_prompt=PRO_LAWYER_PROMPT,
            temperature=0.6,
            max_tokens=1024,
            top_p=0.95,
        )
        self._anti = GroqClient(
            api_key=api_key,
            model=MODEL_ANTI_LAWYER,
            system_prompt=ANTI_LAWYER_PROMPT,
            temperature=0.7,
            max_tokens=1024,
        )

    def argue(
        self,
        claim: str,
        questions: list[str],
        context: SearchContext,
    ) -> DebateRound:
        """Run one debate round: pro argues first, anti critiques."""
        evidence_text = context.formatted
        questions_text = "\n".join(f"- {q}" for q in questions) if questions else "No specific questions."

        # Pro argues first
        pro_prompt = (
            f"CLAIM: {claim}\n\n"
            f"EVIDENCE FROM SEARCH:\n{evidence_text}\n\n"
            f"VERIFICATION QUESTIONS:\n{questions_text}\n\n"
            "Using ONLY the evidence above, argue that this claim is TRUE. "
            "Address each verification question. Cite specific sources by number. "
            "Be concise (max 200 words)."
        )

        try:
            _, pro_argument = self._pro.chat_with_thinking(pro_prompt)
        except Exception as e:
            logger.error("Pro lawyer failed: {}", e)
            pro_argument = "Pro lawyer was unable to formulate an argument."

        # Anti critiques pro's argument
        anti_prompt = (
            f"CLAIM: {claim}\n\n"
            f"EVIDENCE FROM SEARCH:\n{evidence_text}\n\n"
            f"PRO LAWYER'S ARGUMENT:\n{pro_argument}\n\n"
            "Critique the pro lawyer's argument. Point out:\n"
            "- Weak or missing evidence\n"
            "- Logical fallacies\n"
            "- Counter-evidence from the search results\n"
            "- Reasons the claim could be FALSE or UNVERIFIABLE\n"
            "Be concise (max 150 words)."
        )

        try:
            anti_argument = self._anti.chat(anti_prompt)
        except Exception as e:
            logger.error("Anti lawyer failed: {}", e)
            anti_argument = "Anti lawyer was unable to formulate a critique."

        return DebateRound(
            claim=claim,
            questions=questions,
            pro_argument=pro_argument,
            anti_argument=anti_argument,
        )
