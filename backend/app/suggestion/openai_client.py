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
        # The SDK appends `/chat/completions` itself, so `base_url` must be
        # the v1 root. Tolerate ops mistakenly including the suffix (as some
        # provider docs show it) by stripping it here — otherwise Groq sees
        # `.../chat/completions/chat/completions` and returns 404.
        base = settings.openai_base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        kwargs["base_url"] = base
    _cached_key = settings.openai_api_key
    _cached_client = AsyncOpenAI(**kwargs)
    return _cached_client


OPENAI_MODEL = settings.openai_model or "gpt-4o-mini"
