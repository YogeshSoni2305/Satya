"""
EvidenceService — structured evidence extraction using LLM.

Extracts relevant evidence sentences from search results,
classifying each as supporting, contradicting, or neutral.
"""

from backend.utils.logger import logger
from backend.core.llm import GroqClient
from backend.core.constants import MODEL_FORMATTER, MAX_EVIDENCE
from backend.schemas.internal import (
    SearchContext, EvidenceItem, EvidenceContext, NormalizedClaim,
)

EVIDENCE_EXTRACTION_PROMPT = """You are an evidence extraction engine.

Given a CLAIM and SEARCH RESULTS, extract the most relevant evidence sentences.

For each piece of evidence, classify it as:
- "supports" — directly supports the claim
- "contradicts" — directly contradicts the claim  
- "neutral" — relevant but neither supports nor contradicts

Return ONLY valid JSON:
{
  "evidence": [
    {
      "text": "The exact relevant sentence or fact (max 100 chars)",
      "source_index": 1,
      "supports_claim": "supports" | "contradicts" | "neutral",
      "relevance": "high" | "medium" | "low"
    }
  ]
}

RULES:
- Extract max 10 evidence items
- Prioritize high-relevance items
- Use exact text from sources, do not paraphrase
- If no relevant evidence, return {"evidence": []}
- No markdown. No extra text. JSON only.
"""


class EvidenceService:
    """Extracts and classifies evidence from search results."""

    def __init__(self, api_key: str) -> None:
        self._client = GroqClient(
            api_key=api_key,
            model=MODEL_FORMATTER,
            system_prompt=EVIDENCE_EXTRACTION_PROMPT,
            temperature=0.1,
            max_tokens=1024,
        )

    def extract(self, claim: NormalizedClaim, context: SearchContext) -> EvidenceContext:
        """Extract structured evidence items from search results."""
        prompt = (
            f"CLAIM: {claim.claim}\n\n"
            f"SEARCH RESULTS:\n{context.formatted}\n\n"
            "Extract the most relevant evidence from these search results."
        )

        try:
            result = self._client.chat_json(prompt)
            raw_items = result.get("evidence", [])
        except Exception as e:
            logger.warning("Evidence extraction failed: {}", e)
            raw_items = []

        # Build evidence items, linking back to source URLs
        items: list[EvidenceItem] = []
        for raw in raw_items[:MAX_EVIDENCE]:
            if not isinstance(raw, dict):
                continue
            src_idx = raw.get("source_index", 0)
            source_url, source_title = "", ""
            if 1 <= src_idx <= len(context.results):
                source_url = context.results[src_idx - 1].url
                source_title = context.results[src_idx - 1].title

            # Normalize supports_claim to allow weak labels
            sc = (raw.get("supports_claim") or "").strip().lower()
            if sc in ("supports", "support", "supports_claim"):
                sc = "supports"
            elif sc in ("contradicts", "contradict", "contradiction"):
                sc = "contradicts"
            elif sc in ("weak_support", "weak_supports", "weak support"):
                sc = "weak_supports"
            elif sc in ("weak_contradict", "weak_contradicts", "weak contradict"):
                sc = "weak_contradicts"
            else:
                sc = "neutral"

            items.append(EvidenceItem(
                text=raw.get("text", "")[:200],
                source_url=source_url,
                source_title=source_title,
                relevance=raw.get("relevance", "medium"),
                supports_claim=sc,
            ))


        supporting = sum(1 for i in items if i.supports_claim == "supports")
        contradicting = sum(1 for i in items if i.supports_claim == "contradicts")
        weak_support = sum(1 for i in items if i.supports_claim == "weak_supports")
        weak_contradict = sum(1 for i in items if i.supports_claim == "weak_contradicts")
        neutral = sum(1 for i in items if i.supports_claim == "neutral")

        # If everything is neutral, attempt a heuristic to label one weak support/contradiction
        if supporting + contradicting + weak_support + weak_contradict == 0 and items:
            support_keywords = ("confirm", "confirms", "supports", "verif", "found that", "indicate", "shows", "according to")
            contradict_keywords = ("deny", "denies", "contradict", "refute", "debunk", "no evidence", "not true", "disputes")
            assigned = False
            for idx, it in enumerate(items):
                text = f"{it.text} {it.source_title}".lower()
                if any(k in text for k in support_keywords):
                    items[idx].supports_claim = "weak_supports"
                    weak_support += 1
                    neutral -= 1 if neutral > 0 else 0
                    assigned = True
                    break
                if any(k in text for k in contradict_keywords):
                    items[idx].supports_claim = "weak_contradicts"
                    weak_contradict += 1
                    neutral -= 1 if neutral > 0 else 0
                    assigned = True
                    break

            # If still unassigned, mark the first item as weak_supports by default
            if not assigned:
                items[0].supports_claim = "weak_supports"
                weak_support += 1
                neutral -= 1 if neutral > 0 else 0

        logger.info(
            "Extracted {} evidence items: {} supporting, {} weak_support, {} contradicting, {} weak_contradict, {} neutral",
            len(items), supporting, weak_support, contradicting, weak_contradict, neutral,
        )

        return EvidenceContext(
            items=items,
            supporting_count=supporting + weak_support,
            contradicting_count=contradicting + weak_contradict,
            neutral_count=neutral,
        )
