# from google import genai
# from google.genai import types
# from pydantic import BaseModel, Field
# import json

# # ==========================
# # Final single-round schema
# # ==========================
# class FinalDebateResult(BaseModel):
#     verdict: str = Field(..., description="Final verdict: True, False, or Unverifiable")
#     confidence: float = Field(..., description="Confidence score between 0 and 1")
#     conclusion: str = Field(..., description="Short paragraph summarizing the final reasoning and decision (<=50 words)")
#     evidence_summary: str = Field(..., description="Summary of strongest evidence or key missing piece (<=30 words)")

# # ==========================
# # Single-round arbiter class
# # ==========================
# class GeminiIntermediate:
#     def __init__(
#         self, api_key,
#         model_name="gemini-2.0-flash-lite",
#         temperature=0.3,
#         top_p=0.9,
#         top_k=40,
#         max_output_tokens=512,
#         system_prompt="You are the final arbiter deciding truthfulness of a claim based on two arguments."
#     ):
#         self.model_name = model_name
#         self.client = genai.Client(api_key=api_key)
#         self.chat = self.client.chats.create(model=self.model_name)
#         self.config = types.GenerateContentConfig(
#             temperature=temperature,
#             top_p=top_p,
#             top_k=top_k,
#             max_output_tokens=max_output_tokens,
#             system_instruction=[types.Part.from_text(text=system_prompt)],
#             response_mime_type="application/json",
#             response_schema=FinalDebateResult
#         )

#     def send_message(self, claim, llama_response, deepseek_response):
#         prompt = f"""
# You are the final arbiter deciding the truthfulness of a claim.
# You are given the claim, DeepSeek’s fact-checking verdict, and LLaMA’s critique.

# Claim:
# {claim}

# DeepSeek’s Analysis:
# {deepseek_response}

# LLaMA’s Critique:
# {llama_response}

# Evaluate both and return the final JSON with:
# - verdict: "True", "False", or "Unverifiable"
# - confidence: 0.00–1.00
# - conclusion: one short paragraph (why and how you decided)
# - evidence_summary: main supporting or missing evidence (<=30 words)
# """
#         response = self.chat.send_message(prompt, config=self.config)
#         try:
#             return json.loads(response.text)
#         except json.JSONDecodeError:
#             print("Could not convert to JSON, returning raw string.")
#             return response.text

#     def get_history(self):
#         history = []
#         for message in self.chat.get_history():
#             history.append(f"role - {message.role}: {message.parts[0].text}")
#         return history








import json
from groq import Groq
from pydantic import BaseModel, Field, ValidationError
import os
# ==========================
# Final single-round schema
# ==========================
class FinalDebateResult(BaseModel):
    verdict: str = Field(..., description="Final verdict: True, False, or Unverifiable")
    confidence: float = Field(..., ge=0.0, le=1.0)
    conclusion: str = Field(..., description="Short paragraph summarizing the final reasoning (<=50 words)")
    evidence_summary: str = Field(..., description="Strongest evidence or missing piece (<=30 words)")


# ==========================
# Single-round arbiter class
# ==========================
class GroqIntermediate:
    def __init__(
        self,
        api_key: str,
        model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct",
        temperature: float = 0.3,
        max_output_tokens: int = 512,
        system_prompt: str = "You are the final arbiter deciding truthfulness of a claim based on two arguments."
    ):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.system_prompt = system_prompt

    def send_message(self, claim, llama_response, deepseek_response):
        prompt = f"""
Return ONLY valid JSON matching this schema exactly:

{FinalDebateResult.model_json_schema()}

Claim:
{claim}

DeepSeek’s Analysis:
{deepseek_response}

LLaMA’s Critique:
{llama_response}

Rules:
- verdict must be one of: "True", "False", "Unverifiable"
- confidence must be between 0 and 1
- No markdown, no explanations, no extra text
"""

        completion = self.client.chat.completions.create(
            model=self.model_name,
            temperature=self.temperature,
            max_completion_tokens=self.max_output_tokens,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
        )

        raw_output = completion.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw_output)
            validated = FinalDebateResult(**parsed)
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            print("❌ JSON validation failed")
            print("Raw model output:")
            print(raw_output)
            raise e

    def get_history(self):
        # Groq is stateless; kept only for interface compatibility
        return []
