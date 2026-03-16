"""
Global constants extracted from fighter.py and model files.

Single source of truth for trusted news sources and LLM model identifiers.
"""

# ── Trusted News Sources ──────────────────────────────────────
# Used by SearchService to prioritize credible domains.
TRUSTED_SOURCES: list[str] = [
    # International verified outlets
    "reuters.com", "bbc.com", "apnews.com", "theguardian.com",
    "nytimes.com", "washingtonpost.com", "factcheck.org",
    "politifact.com", "snopes.com", "who.int", "cdc.gov",
    "nature.com", "bloomberg.com", "forbes.com", "economist.com",
    # Credible Indian outlets
    "thehindu.com", "hindustantimes.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "ndtv.com", "factly.in",
    "boomlive.in", "altnews.in", "scroll.in", "moneycontrol.com",
    "livemint.com", "newslaundry.com",
]

# ── LLM Model Identifiers (Groq-hosted) ──────────────────────
MODEL_PRO_LAWYER = "llama-3.3-70b-versatile"   # Pro-truth advocate
MODEL_ANTI_LAWYER = "llama-3.3-70b-versatile"  # Skeptical critic
MODEL_JUDGE = "llama-3.3-70b-versatile"        # Final arbiter
MODEL_FORMATTER = "llama-3.1-8b-instant"       # Formatting / short tasks
# ── Pipeline Limits (V1) ─────────────────────────────────────
MAX_CLAIMS = 3              # Maximum claims to process per request
MAX_SEARCH_RESULTS = 6      # Maximum search results to keep after merging
MAX_CLAIM_LENGTH = 5000     # Maximum input text length (characters)
MIN_CLAIM_LENGTH = 10       # Minimum input text length (characters)

# ── Pipeline Limits (V2) ─────────────────────────────────────
MAX_CONTEXT = 8             # Maximum sources in final merged context
MAX_QUESTIONS = 3           # Maximum verification questions from judge
MAX_SEARCH_CALLS = 4        # Maximum total search API calls per request
MAX_EVIDENCE = 10           # Maximum extracted evidence sentences
MAX_DEBATE_TOKENS = 800     # Maximum tokens per debate argument

# ── Domain Reliability Scores ─────────────────────────────────
# Used by ReliabilityService to score sources. 1.0 = highest trust.
DOMAIN_RELIABILITY: dict[str, float] = {
    # Tier 1: Dedicated fact-checkers & agencies (0.95–1.0)
    "factcheck.org": 1.0, "politifact.com": 1.0, "snopes.com": 0.98,
    "factly.in": 0.97, "boomlive.in": 0.97, "altnews.in": 0.96,
    "reuters.com": 0.95, "apnews.com": 0.95,
    # Tier 2: Authoritative institutions (0.90–0.94)
    "who.int": 0.94, "cdc.gov": 0.94, "nature.com": 0.93,
    # Tier 3: Major international outlets (0.80–0.89)
    "bbc.com": 0.88, "theguardian.com": 0.87, "nytimes.com": 0.87,
    "washingtonpost.com": 0.86, "bloomberg.com": 0.85,
    "economist.com": 0.85, "forbes.com": 0.82,
    # Tier 4: Indian national outlets (0.70–0.79)
    "thehindu.com": 0.79, "ndtv.com": 0.78, "indiatoday.in": 0.76,
    "hindustantimes.com": 0.75, "livemint.com": 0.75,
    "timesofindia.indiatimes.com": 0.73, "scroll.in": 0.72,
    "moneycontrol.com": 0.70, "newslaundry.com": 0.70,
}
# Default score for unknown domains
DEFAULT_DOMAIN_SCORE = 0.4

