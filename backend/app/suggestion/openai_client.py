"""Shared OpenAI client accessor — returns None if no API key is configured."""

from __future__ import annotations

from app.core.config import settings

_cached_client = None
_cached_key = None


def get_openai_client():
    """Return an AsyncOpenAI client, or None when OPENAI_API_KEY is unset.

    Callers must handle the None case (graceful degradation to non-LLM paths).
    Re-creates the client if the API key changes at runtime.
    """
    global _cached_client, _cached_key
    if not settings.openai_api_key:
        return None
    if _cached_client is not None and _cached_key == settings.openai_api_key:
        return _cached_client
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    _cached_key = settings.openai_api_key
    _cached_client = AsyncOpenAI(**kwargs)
    return _cached_client


OPENAI_MODEL = settings.openai_model or "gpt-4o-mini"
