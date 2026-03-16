"""
Search-related prompts.

Currently a placeholder — the search service constructs
its own query strings. This module exists for future
LLM-based query refinement.
"""

SEARCH_QUERY_PROMPT = """Given a user's claim, generate a concise search query 
that will find evidence to verify or debunk the claim.

RULES:
- Max 120 characters
- Focus on the key factual assertion
- Include relevant entities (names, dates, places)
- Do not include opinions or subjective language
- Return ONLY the search query string, nothing else
"""
