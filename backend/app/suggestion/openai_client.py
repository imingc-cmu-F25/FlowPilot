"""Shared OpenAI client accessor — returns None if no API key is configured."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_openai_client():
    """Return an AsyncOpenAI client, or None when OPENAI_API_KEY is unset.

    Callers must handle the None case (graceful degradation to non-LLM paths).
    """
    if not settings.openai_api_key:
        return None
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None
    return AsyncOpenAI(api_key=settings.openai_api_key)


OPENAI_MODEL = "gpt-4o-mini"
