"""
ClaimService — claim normalization using LLM.

Extracts a clean factual claim, entities, time references, and topic from raw user input.
"""

from backend.utils.logger import logger
from backend.core.llm import GroqClient
from backend.core.constants import MODEL_FORMATTER
from backend.schemas.internal import NormalizedClaim

CLAIM_NORMALIZE_PROMPT = """You are a claim normalization engine.

Given raw input text, extract and return a clean, structured JSON:

{
  "claim": "The single core factual claim (max 200 chars, neutral tone)",
  "entities": ["list", "of", "named", "entities"],
  "time_reference": "any date/time mentioned or 'unspecified'",
  "topic": "one of: politics | health | science | technology | economics | sports | entertainment | environment | other"
}

RULES:
- Remove opinions, emotions, rhetorical language
- Keep only the verifiable factual assertion
- If multiple claims, pick the primary one
- Entities = people, organizations, places, events
- No markdown. No extra text. JSON only.
"""


class ClaimService:
    """Normalizes raw user text into structured claim data."""

    def __init__(self, api_key: str) -> None:
        self._client = GroqClient(
            api_key=api_key,
            model=MODEL_FORMATTER,
            system_prompt=CLAIM_NORMALIZE_PROMPT,
            temperature=0.1,
            max_tokens=512,
        )

    def normalize(self, text: str) -> NormalizedClaim:
        """Normalize raw input into a structured claim. Falls back to raw text on error."""
        try:
            result = self._client.chat_json(f"Normalize this input:\n\n{text}", schema=NormalizedClaim)
            normalized = NormalizedClaim(**result)
            normalized.original_text = text
            if not normalized.claim.strip():
                normalized.claim = text
            logger.info("Claim normalized: '{}' → '{}'", text[:50], normalized.claim[:50])
            return normalized
        except Exception as e:
            logger.warning("Claim normalization failed, using raw text: {}", e)
            return NormalizedClaim(
                claim=text,
                original_text=text,
                entities=[],
                time_reference="unspecified",
                topic="other",
            )
