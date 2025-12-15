from system_prompts import *
import models
import os
import config
from dotenv import load_dotenv
from colorama import Fore, Style, init
from tavily_search import tavily_search
from preprocessor import Description
import warnings
import asyncio
import json
from pathlib import Path
from config import *

warnings.filterwarnings("ignore")
init()

# === Trusted News Sources (Global Constant) ===
TRUSTED_SOURCES = [
    # 🌍 International verified outlets
    "reuters.com", "bbc.com", "apnews.com", "theguardian.com",
    "nytimes.com", "washingtonpost.com", "factcheck.org",
    "politifact.com", "snopes.com", "who.int", "cdc.gov",
    "nature.com", "bloomberg.com", "forbes.com", "economist.com",

    # 🇮🇳 Credible Indian outlets
    "thehindu.com", "hindustantimes.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "ndtv.com", "factly.in",
    "boomlive.in", "altnews.in", "scroll.in", "moneycontrol.com",
    "livemint.com", "newslaundry.com"
]
def run_pipeline(input_data: dict) -> dict:
    """
    API-safe wrapper for the full fact-checking pipeline.
    """
    fighter = ClaimFighter()
    fighter.run_with_formatter(input_data)
    return fighter.output



class ClaimFighter:
    def __init__(self):
        load_dotenv()

        # Load API keys from environment (no hardcoded fallbacks)
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.tavily_key = os.getenv("TAVILY_API_KEY")

        if not self.groq_key or not self.gemini_key or not self.tavily_key:
            raise ValueError("Missing required API keys. Please set them in api.key or environment variables.")

        print("✅ All API keys are loaded successfully!")

        # Ensure asyncio loop exists
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Initialize models (reuse models module)
        self.llama = models.LlamaChat(api_key=self.groq_key, system_prompt=LLAMA_SYSTEM_PROMPT)
        self.deepseek = models.DeepseekChat(api_key=self.groq_key, system_prompt=DEEPSEEK_SYSTEM_PROMPT)
        self.gemini_chat = models.GeminiChat(api_key=self.gemini_key, system_prompt=GEMINI_EXTRACTOR_SYSTEM_PROMPT)
        self.gemini_arbitrator = models.GeminiIntermediate(api_key=self.gemini_key, system_prompt=GEMINI_INTERMEDIATE_SYSTEM_PROMPT)

        # store trusted sources locally as well (in case you want to change per instance)
        self.trusted_sources = TRUSTED_SOURCES.copy()

        # output container
        self.output = {}

        # ensure result dir exist (defensive)
        Path(RESULT_DIR).mkdir(parents=True, exist_ok=True)


    def from_formatter(self, formatter_output: dict):
        master_text = formatter_output.get("master_input_text", "")
        tavily_query = formatter_output.get("tavily_query", "")

        print("🔍 Tavily Query:", tavily_query)

        # Step 3: Tavily Search
        tavily_results = self.fetch_tavily_sources(tavily_query)

        # Step 4: Gemini Claim Extraction
        gemini_input = {
            "master_input_text": master_text,
            # "tavily_evidence": tavily_results
        }

        extracted_claims = self.extract_claims(gemini_input)

        return extracted_claims, tavily_results


    # ----------------------------
    # Claim Extraction
    # ----------------------------
    def extract_claims(self, message: dict) -> dict:
        """Extract factual claims and questions from the input using Gemini extractor."""
        # reuse self.gemini_chat (keeps conversation history if needed)
        try:
            response = self.gemini_chat.send_message(str(message))
        except Exception as e:
            print(f"[EXTRACTOR ERROR] {e}")
            # fallback: return an empty claim structure to avoid breaking pipeline
            return {"claims": []}
        print(f"{Fore.MAGENTA}RESPONSE FROM CLAIM EXTRACTOR (GEMINI):{Style.RESET_ALL}")
        print(response)
        return response

    # ----------------------------
    # Save Markdown Utility
    # ----------------------------
    def save_to_markdown(self, content: str, filename: Path = None, mode: str = "a"):
        """Save content to markdown in RESULT_DIR by default."""
        if filename is None:
            filename = Path(RESULT_DIR) / "claim_fighter_results.md"
        # ensure parent exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, mode, encoding="utf-8") as md_file:
            md_file.write(content)

    # ----------------------------
    # Tavily Fact-Check Fetcher (trusted-first, fallback if avg score < 80)
    # ----------------------------
    def fetch_tavily_sources(self, claim_text: str, trusted_only_max_results: int = 10, fallback_max_results: int = 10):
        """
        Fetch fact-check sources related to the claim using Tavily.
        Strategy:
         1) Search trusted domains only (include_domains=self.trusted_sources)
         2) If avg score < 80 OR too few results (<3), retry without include_domains
         3) Return formatted list sorted by Tavily's 'score'
        """
        print(f"🔍 Fetching Tavily sources for: {claim_text}")

        def format_results(raw_results):
            formatted_local = []
            for r in raw_results:
                # try multiple possible fields for snippets/content
                snippet = r.get("snippet") or r.get("content") or r.get("summary") or ""
                formatted_local.append({
                    "title": r.get("title", "Untitled"),
                    "url": r.get("url", "#"),
                    "score": round(r.get("score", 0), 2) if isinstance(r.get("score", 0), (int, float)) else r.get("score", r.get("score", "N/A")),
                    "snippet": (snippet[:300] + "...") if snippet and len(snippet) > 300 else snippet
                })
            # sort by score descending if numeric
            formatted_local.sort(key=lambda x: (x["score"] if isinstance(x["score"], (int, float)) else 0), reverse=True)
            return formatted_local

        try:
            # Step 1: trusted-only search
            tavily_resp = tavily_search(
                query=f"Verify this claim with evidence: {claim_text}. Prefer primary, peer-reviewed, or official sources.",
                topic="news",
                search_depth="advanced",
                max_results=trusted_only_max_results,
                include_domains=self.trusted_sources,
                include_answer=True,
                include_raw_content=True,
                TAVILY_API_KEY=self.tavily_key
            )

            primary_results = tavily_resp.get("results", []) or []
            formatted_primary = format_results(primary_results)

            # compute avg score only among numeric scores
            numeric_scores = [r.get("score") for r in primary_results if isinstance(r.get("score"), (int, float))]
            avg_score = (sum(numeric_scores) / len(numeric_scores)) if numeric_scores else 0
            print(f"📊 Tavily (trusted) returned {len(primary_results)} results, avg score = {avg_score:.2f}")

            # fallback conditions: too few results OR low avg score
            if len(primary_results) < 3 or avg_score < 80:
                print("🔄 Trusted search insufficient (few results or low relevance). Retrying without domain restriction...")
                tavily_resp = tavily_search(
                    query=f"Verify this claim with evidence: {claim_text}. Include all relevant public sources and official reports.",
                    topic="news",
                    search_depth="advanced",
                    max_results=fallback_max_results,
                    include_answer=True,
                    include_raw_content=True,
                    TAVILY_API_KEY=self.tavily_key
                )
                fallback_results = tavily_resp.get("results", []) or []
                formatted_fallback = format_results(fallback_results)
                # prefer trusted results first, then append top fallback items not already present (by URL)
                urls_seen = {r["url"] for r in formatted_primary}
                merged = formatted_primary.copy()
                for r in formatted_fallback:
                    if r["url"] not in urls_seen:
                        merged.append(r)
                        urls_seen.add(r["url"])
                # final trimming and sorting
                merged.sort(key=lambda x: (x["score"] if isinstance(x["score"], (int, float)) else 0), reverse=True)
                return merged[:6]
            else:
                return formatted_primary[:6]

        except Exception as e:
            print(f"[TAVILY ERROR] {e}")
            return []

    # ----------------------------
    # One-Round Debate
    # ----------------------------
    def fight(self, response):
        """Run one-round debate with reasoning + fact-check sources"""
        markdown_content = "## Debate Results (Single Round)\n\n"

        # guard if no claims
        claims_list = []
        try:
            claims_list = response[0].get("claims", []) if isinstance(response, (list, tuple)) and response else response.get("claims", []) if isinstance(response, dict) else []
        except Exception:
            claims_list = []

        if not claims_list:
            print("[WARNING] No claims found to process.")
            self.save_to_markdown("## No claims extracted.\n")
            return

        for idx, claim in enumerate(claims_list[:3]):
            print(f"\n{Fore.YELLOW}=== CLAIM ({claim}) ==={Style.RESET_ALL}")
            markdown_content += f"### Claim: {claim}\n\n"

            claim_key = f"claim{idx}"
            self.output[claim_key] = {"claim": claim}

            # === DeepSeek turn ===
            try:
                _, deepseek_response = self.deepseek.send_message(claim)
            except Exception as e:
                print(f"[DEEPSEEK ERROR] {e}")
                deepseek_response = "No response or token limit exceeded."
            deepseek_response = deepseek_response or "No response or token limit exceeded."
            markdown_content += f"**DeepSeek Response:**\n\n```\n{deepseek_response}\n```\n\n"

            # === LLaMA turn ===
            try:
                llama_response = self.llama.send_message(f"Claim: {claim}\nOpponent: {deepseek_response}")
            except Exception as e:
                print(f"[LLAMA ERROR] {e}")
                llama_response = "No response."
            markdown_content += f"**LLaMA Response:**\n\n```\n{llama_response}\n```\n\n"

            # === Gemini Arbitrator (Final Verdict) ===
            try:
                gemini_response = self.gemini_arbitrator.send_message(
                    claim=claim,
                    llama_response=llama_response,
                    deepseek_response=deepseek_response
                )
            except Exception as e:
                print(f"[GEMINI ARBITRATOR ERROR] {e}")
                gemini_response = {}
            markdown_content += f"**Gemini Arbitrator Verdict:**\n\n```\n{json.dumps(gemini_response, indent=2)}\n```\n\n"

            # === Tavily fact-check sources ===
            tavily_sources = self.fetch_tavily_sources(claim)
            markdown_content += "**Fact-Check Sources:**\n\n"
            if tavily_sources:
                for src in tavily_sources:
                    # show score safely
                    score_display = src.get("score", "N/A")
                    markdown_content += f"- [{src['title']}]({src['url']}) — Score: {score_display}\n"
            else:
                markdown_content += "_No reliable sources found._\n"
            markdown_content += "\n"

            # === Combine final reasoning and confidence ===
            final_reasoning = gemini_response.get("evidence_summary", "No reasoning provided.") if isinstance(gemini_response, dict) else "No reasoning provided."
            confidence = gemini_response.get("confidence", "Unknown") if isinstance(gemini_response, dict) else "Unknown"
            conclusion = gemini_response.get("conclusion", "No conclusion generated.") if isinstance(gemini_response, dict) else "No conclusion generated."

            markdown_content += f"**Final Verdict:**\n\n{conclusion}\n\n"
            markdown_content += f"**Reasoning:** {final_reasoning}\n\n"
            markdown_content += f"**Confidence:** {confidence}\n\n"
            markdown_content += "---\n\n"

            # Save to structured output
            self.output[claim_key].update({
                "deepseek_response": deepseek_response,
                "llama_response": llama_response,
                "gemini_response": gemini_response,
                "tavily_sources": tavily_sources,
                "final_conclusion": conclusion,
                "confidence": confidence
            })

        # Save results
        self.save_to_markdown(markdown_content)
        output_json_path = Path(RESULT_DIR) / "output.json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(self.output, f, ensure_ascii=False, indent=4)
        print("✅ Output saved to output.json and claim_fighter_results.md")

    # ----------------------------
    # Run Full Pipeline
    # ----------------------------
    def run(self, inputs: dict):
        try:
            # Markdown header
            markdown_header = "# ClaimFighter Results\n\n## User Inputs\n\n"
            for key, value in inputs.items():
                if value:
                    markdown_header += f"- **{key.upper()}**: {value}\n"
            markdown_header += "\n---\n\n"
            # overwrite existing file for a fresh session
            self.save_to_markdown(markdown_header, mode="w")

            # Preprocessing
            desc = Description()
            results = desc.process(inputs)
            self.output["inputs"] = inputs
            self.output["descr"] = results
            print("✅ Preprocessing completed.")

            preprocessed_md = "## Preprocessed Content\n\n"
            for key, value in results.items():
                preprocessed_md += f"### {key.upper()} Content\n\n```\n{value}\n```\n\n"
            preprocessed_md += "---\n\n"
            self.save_to_markdown(preprocessed_md)

            # Claim extraction
            claims = self.extract_claims(results)
            claims_md = "## Extracted Claims\n\n```\n" + str(claims) + "\n```\n\n"
            self.save_to_markdown(claims_md)

            # Fight one round
            self.fight(claims)
            print(f"\n{Fore.GREEN}Results successfully saved ✅{Style.RESET_ALL}")

        except Exception as e:
            print(f"[ERROR] {e}")
            # append error to markdown
            self.save_to_markdown(f"\n\n## Error\n\n```\n{str(e)}\n```\n")

    def run_with_formatter(self, user_inputs: dict):
        """
        Full fact-check pipeline:
        1. Preprocessing
        2. Groq Formatter → master_input_text + tavily_query
        3. Tavily Search
        4. Gemini Claim Extraction (with evidence)
        5. Debate Workflow
        6. Save Outputs
        """
        from groq_processing import run_full_pipeline

        print("\n🔧 STEP 1 — Preprocessing + Formatter (Groq)")
        formatter_output = run_full_pipeline(user_inputs)

        # --- SAFETY CHECK ---
        if isinstance(formatter_output, str):
            try:
                formatter_output = formatter_output.strip()

                # Remove markdown/code fences if present
                if formatter_output.startswith("```"):
                    formatter_output = formatter_output.split("```")[1]

                formatter_output = json.loads(formatter_output)
            except Exception as e:
                raise ValueError(
                    f"Formatter did not return valid JSON.\n"
                    f"Raw output:\n{formatter_output}"
                )

        if not isinstance(formatter_output, dict):
            raise TypeError("Formatter output must be a dict.")
        # --------------------

        master_text = formatter_output.get("master_input_text", "")
        tavily_query = formatter_output.get("tavily_query", "")

        tavily_query = formatter_output.get("tavily_query", "")

        print("\n🎯 MASTER INPUT TEXT:")
        print(master_text)

        print("\n🔍 TAVILY QUERY:")
        print(tavily_query)

        # STEP 2 — Tavily Search
        print("\n🌐 STEP 2 — Fetching Tavily Evidence…")
        tavily_evidence = self.fetch_tavily_sources(tavily_query)

        # STEP 3 — Gemini Claim Extraction
        print("\n🧠 STEP 3 — Extracting Claims with Gemini…")
        gemini_input = {
            "master_input_text": master_text,
            # "tavily_evidence": tavily_evidence
        }
        extracted_claims = self.extract_claims(gemini_input)

        print("\n📌 Extracted Claims:")
        print(extracted_claims)

        # STEP 4 — Debate Round
        print("\n⚔️ STEP 4 — Running Debate Workflow…")
        self.fight(extracted_claims)

        print("\n✅ PIPELINE COMPLETE")


# ----------------------------
# Main Execution
# ----------------------------
if __name__ == "__main__":
    fighter = ClaimFighter()
    input_data = {
        "text": "Donald Trump has increased tariffs to demonstrate his power over other countries.",
        "image": str(Path(BASE_DIR) / "data" / "donald.jpg"),
        "video": None,
        "audio": str(Path(BASE_DIR) / "data" / "donaltrump.mp3"),
        "url": "https://www.firstpost.com/explainers/donald-trump-liberation-day-tariff-90-day-pause-explained-13878689.html"
    }

    # fighter.run(input_data)
    fighter.run_with_formatter(input_data)






# import os, json
# from pathlib import Path
# from dotenv import load_dotenv
# from tavily_search import tavily_search
# from preprocessor import Description
# import models
# from system_prompts import *

# RESULT_DIR = Path("results")
# RESULT_DIR.mkdir(exist_ok=True)

# TRUSTED_SOURCES = [
#     "reuters.com", "bbc.com", "apnews.com", "theguardian.com",
#     "nytimes.com", "washingtonpost.com", "factcheck.org",
#     "politifact.com", "snopes.com", "who.int", "cdc.gov",
#     "nature.com", "bloomberg.com", "economist.com",
#     "thehindu.com", "ndtv.com", "altnews.in", "boomlive.in"
# ]


# class ClaimFighter:
#     def __init__(self):
#         load_dotenv()

#         self.groq_key = os.getenv("GROQ_API_KEY")
#         self.gemini_key = os.getenv("GEMINI_API_KEY")
#         self.tavily_key = os.getenv("TAVILY_API_KEY")

#         if not all([self.groq_key, self.gemini_key, self.tavily_key]):
#             raise RuntimeError("Missing API keys")

#         # Models
#         self.formatter = models.LlamaChat(self.groq_key, LLAMA_SYSTEM_PROMPT)
#         self.extractor = models.GeminiChat(self.gemini_key, GEMINI_EXTRACTOR_SYSTEM_PROMPT)
#         self.deepseek = models.DeepseekChat(self.groq_key, DEEPSEEK_SYSTEM_PROMPT)
#         self.llama = models.LlamaChat(self.groq_key, LLAMA_SYSTEM_PROMPT)
#         self.arbitrator = models.GeminiIntermediate(
#             self.gemini_key, GEMINI_INTERMEDIATE_SYSTEM_PROMPT
#         )

#         self.output = {}

#     # -------------------------
#     # PIPELINE ENTRY POINT
#     # -------------------------
#     def run(self, user_inputs: dict):
#         preprocessed = self.preprocess(user_inputs)
#         formatted = self.format(preprocessed)
#         claims = self.extract_claims(formatted["master_input_text"])

#         results = []
#         for claim in claims:
#             results.append(self.process_claim(claim))

#         self.save(results)
#         return results

#     # -------------------------
#     # STAGES
#     # -------------------------
#     def preprocess(self, inputs):
#         return Description().process(inputs)

#     def format(self, preprocessed):
#         from groq_processing import run_full_pipeline
#         return run_full_pipeline(preprocessed)

#     def extract_claims(self, text):
#         raw = self.extractor.send_message(text)
#         claims = self._safe_parse_claims(raw)
#         return claims[:3]

#     def process_claim(self, claim: str):
#         sources = self.fetch_sources(claim)

#         if self.needs_debate(claim):
#             ds = self.deepseek.send_message(claim)[1]
#             ll = self.llama.send_message(f"Claim: {claim}\nOpponent: {ds}")
#         else:
#             ds = ll = "Skipped (simple factual claim)"

#         verdict = self.arbitrate(claim, ds, ll, sources)

#         return {
#             "claim": claim,
#             "sources": sources,
#             "deepseek": ds,
#             "llama": ll,
#             "verdict": verdict
#         }

#     # -------------------------
#     # HELPERS
#     # -------------------------
#     def fetch_sources(self, claim):
#         response = tavily_search(
#             query=f"Verify this claim: {claim}",
#             search_depth="advanced",
#             max_results=8,
#             include_domains=TRUSTED_SOURCES,
#             TAVILY_API_KEY=self.tavily_key
#         )
#         return response.get("results", [])

#     def arbitrate(self, claim, ds, ll, sources):
#         return self.arbitrator.send_message(
#             claim=claim,
#             deepseek_response=ds,
#             llama_response=ll,
#             sources=sources
#         )

#     def needs_debate(self, claim):
#         return any(word in claim.lower() for word in ["because", "caused", "intended"])

#     def save(self, data):
#         with open(RESULT_DIR / "output.json", "w") as f:
#             json.dump(data, f, indent=2)

#     def _safe_parse_claims(self, raw):
#         try:
#             parsed = json.loads(raw)
#             return parsed.get("claims", [])
#         except Exception:
#             return []
