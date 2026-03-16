"""
JSON extraction and parsing utilities.

Extracted from groq_processing.py and fighter.py to provide
safe, reusable JSON helpers for all services.
"""

import json
import re


def extract_json_object(text: str) -> dict:
    """
    Extract the first valid JSON object from a string.

    Handles LLM outputs that include markdown fences, preambles,
    or trailing text around the actual JSON payload.
    """
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag) and closing fence
        lines = cleaned.split("\n")
        # Find first line after opening fence
        start = 1
        # Find closing fence
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        cleaned = "\n".join(lines[start:end])

    # Try direct parse first (fastest path)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: regex extraction of first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in text: {cleaned[:200]}...")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON extracted: {match.group(0)[:200]}...") from e


def extract_json_array(text: str) -> list:
    """
    Extract the first valid JSON array from a string.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip().startswith("```"):
                end = i
                break
        cleaned = "\n".join(lines[start:end])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in text: {cleaned[:200]}...")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON array: {match.group(0)[:200]}...") from e
