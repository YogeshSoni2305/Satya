"""
JudgeService — verification questions and final verdict.

Two roles:
1. Generate verification questions BEFORE debate
2. Deliver final verdict AFTER hearing both sides with all V2 signals
"""

from backend.utils.logger import logger
from backend.core.llm import GroqClient
from backend.core.constants import MODEL_JUDGE
from backend.schemas.internal import (
    SearchContext, JudgeVerdict,
    MultiRoundDebate, EvidenceContext,
)


class JudgeService:
    """Generates verification questions and delivers final verdicts."""

    def __init__(self, api_key: str) -> None:
        from backend.prompts.judge import JUDGE_QUESTION_PROMPT, JUDGE_VERDICT_PROMPT

        self._question_client = GroqClient(
            api_key=api_key,
            model=MODEL_JUDGE,
            system_prompt=JUDGE_QUESTION_PROMPT,
            temperature=0.3,
            max_tokens=512,
        )
        self._verdict_client = GroqClient(
            api_key=api_key,
            model=MODEL_JUDGE,
            system_prompt=JUDGE_VERDICT_PROMPT,
            temperature=0.3,
            max_tokens=768,
        )

    def generate_questions(self, claim: str, context: SearchContext) -> list[str]:
        """Generate 2-3 verification questions that test the claim's truthfulness."""
        prompt = (
            f"CLAIM: {claim}\n\n"
            f"AVAILABLE EVIDENCE:\n{context.formatted}\n\n"
            "Generate 2-3 verification questions that:\n"
            "1. Directly test whether this claim is true or false\n"
            "2. Can be answered using the available evidence\n"
            "3. Focus on the most important factual assertions\n\n"
            "Return ONLY a JSON array of question strings.\n"
            'Example: ["Is X supported by evidence?", "Does Y contradict Z?"]\n\n'
            "No markdown. No explanations. Just the JSON array."
        )

        try:
            from backend.utils.json_utils import extract_json_array
            raw = self._question_client.chat(prompt)
            questions = extract_json_array(raw)
            if isinstance(questions, list):
                return [str(q) for q in questions[:3]]
        except Exception as e:
            logger.warning("Question generation failed, using fallback: {}", e)

        return [f"Is the following claim supported by reliable evidence: {claim}"]

    def verdict(
        self,
        claim: str,
        debate: MultiRoundDebate,
        evidence: EvidenceContext,
        context: SearchContext,
        agreement_score: float = 0.5,
    ) -> JudgeVerdict:
        """Deliver verdict using all V2 signals: evidence, debate, reliability, agreement."""
        source_reliability = context.avg_reliability

        prompt = (
            f"CLAIM:\n{claim}\n\n"
            f"EXTRACTED EVIDENCE ({len(evidence.items)} items — "
            f"{evidence.supporting_count} supporting, "
            f"{evidence.contradicting_count} contradicting, "
            f"{evidence.neutral_count} neutral):\n"
            f"{evidence.formatted}\n\n"
            f"DEBATE ROUNDS:\n{debate.formatted}\n\n"
            f"SOURCE RELIABILITY SCORE: {source_reliability:.2f}\n"
            f"EVIDENCE AGREEMENT SCORE: {agreement_score:.2f}\n\n"
            "Deliver your verdict considering ALL signals above.\n\n"
            "Return ONLY valid JSON:\n"
            "{\n"
            '  "verdict": "True" | "False" | "Unverifiable",\n'
            '  "confidence": 0.00 to 1.00,\n'
            '  "conclusion": "max 50 words",\n'
            '  "evidence_summary": "max 30 words",\n'
            '  "agreement_score": 0.00 to 1.00,\n'
            '  "evidence_strength": "strong" | "medium" | "weak" | "none",\n'
            '  "source_reliability": 0.00 to 1.00\n'
            "}\n\n"
            "No markdown. No extra text."
        )

        try:
            return JudgeVerdict(**self._verdict_client.chat_json(prompt, JudgeVerdict))
        except Exception as e:
            logger.error("Verdict generation failed: {}", e)
            return JudgeVerdict(
                verdict="Unverifiable",
                confidence=0.0,
                conclusion="Unable to determine verdict due to processing error.",
                evidence_summary="Verdict generation failed.",
                agreement_score=agreement_score,
                evidence_strength="none",
                source_reliability=source_reliability,
            )
