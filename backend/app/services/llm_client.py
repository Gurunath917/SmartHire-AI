"""
LLM Client Service — OpenAI-compatible API wrapper.

Supports:
  - OpenAI (gpt-3.5-turbo, gpt-4, etc.)
  - Groq  (set OPENAI_API_BASE=https://api.groq.com/openai/v1)
  - Any OpenAI-compatible endpoint

Falls back to rule-based generation if:
  - LLM_API_KEY is not set
  - API call fails
  - Response cannot be parsed

API key and base URL are read from .env — never hardcoded.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from app.config import settings
from app.utils.logger import logger


def _is_llm_configured() -> bool:
    """Return True if an LLM API key is configured."""
    return bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.4,
    expect_json: bool = True,
) -> Optional[str]:
    """
    Send a chat completion request to the configured LLM.

    Args:
        system_prompt: The system instruction.
        user_prompt:   The user message.
        max_tokens:    Maximum response tokens.
        temperature:   Sampling temperature (lower = more deterministic).
        expect_json:   If True, instructs the model to return valid JSON.

    Returns:
        The LLM response string, or None if unavailable/failed.
    """
    if not _is_llm_configured():
        logger.info("LLM_API_KEY not set — skipping LLM call, using fallback.")
        return None

    try:
        from openai import OpenAI

        client_kwargs: dict = {"api_key": settings.LLM_API_KEY}
        if settings.OPENAI_API_BASE:
            client_kwargs["base_url"] = settings.OPENAI_API_BASE

        client = OpenAI(**client_kwargs)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        # Ask for JSON explicitly if needed
        if expect_json:
            messages[0]["content"] += "\n\nYou MUST respond with valid JSON only. No prose, no markdown, no code blocks."

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        logger.info(
            "LLM call succeeded: model={} tokens_used={}",
            settings.LLM_MODEL,
            response.usage.total_tokens if response.usage else "unknown",
        )
        return content

    except ImportError:
        logger.warning("openai package not installed. Run: pip install openai")
        return None
    except Exception as e:
        logger.error("LLM API call failed: {}", e)
        return None


def extract_json_from_response(text: str) -> Optional[dict | list]:
    """
    Parse JSON from LLM response text.
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    if not text:
        return None

    # Strip markdown code blocks if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array or object within the text
    for pattern in [r"\[.*\]", r"\{.*\}"]:
        match = re.search(pattern, cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    logger.warning("Could not parse JSON from LLM response.")
    return None
