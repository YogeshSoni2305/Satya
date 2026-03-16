"""
Unified Groq LLM client.

Stateless wrapper — each call is independent, no message history.
Replaces four old model wrappers (LlamaChat, DeepseekChat, GroqChat, GroqIntermediate).
"""

from typing import Type

from groq import Groq
from pydantic import BaseModel, ValidationError

from backend.utils.logger import logger
from backend.utils.json_utils import extract_json_object


class GroqClient:
    """Stateless Groq chat completions client."""

    def __init__(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
    ) -> None:
        self._client = Groq(api_key=api_key)
        self._model = model
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._top_p = top_p

    def chat(self, user_message: str) -> str:
        """Send a single user message, return assistant's text response."""
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=self._temperature,
                max_completion_tokens=self._max_tokens,
                top_p=self._top_p,
                stream=False,
            )
            content = completion.choices[0].message.content
            if content is None:
                logger.warning("LLM returned None content | model={}", self._model)
                return ""
            return content.strip()

        except Exception as e:
            logger.error("GroqClient.chat failed | model={} | {}", self._model, e)
            raise

    def chat_json(
        self,
        user_message: str,
        schema: Type[BaseModel] | None = None,
    ) -> dict:
        """Send a message and parse response as JSON, optionally validating against a Pydantic schema."""
        raw = self.chat(user_message)

        try:
            parsed = extract_json_object(raw)
        except ValueError:
            logger.error("JSON extraction failed | model={} | raw={}", self._model, raw[:300])
            raise

        if schema is not None:
            try:
                validated = schema(**parsed)
                return validated.model_dump()
            except ValidationError as e:
                logger.error("Schema validation failed | schema={} | {}", schema.__name__, e)
                raise ValueError(f"Schema validation failed: {e}") from e

        return parsed

    def chat_with_thinking(self, user_message: str) -> tuple[str, str]:
        """
        Send a message to a reasoning model with <think> tags.

        Returns (full_response, summary_after_thinking).
        """
        raw = self.chat(user_message)
        marker = "</think>"
        idx = raw.find(marker)
        if idx == -1:
            return raw, raw
        summary = raw[idx + len(marker):].strip()
        return raw, summary
