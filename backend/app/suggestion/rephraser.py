"""AIRephraser — polishes the SuggestionResult content for user-friendly output."""

from __future__ import annotations

from app.suggestion.base import SuggestionResult
from app.suggestion.openai_client import OPENAI_MODEL, get_openai_client


class AIRephraser:
    SYSTEM_PROMPT = (
        "You are an assistant that polishes workflow suggestions. "
        "Rewrite the given text to be clear, friendly, and concise. "
        "Keep it under 3 short sentences. Return plain text, no markdown."
    )

    async def rephrase(self, result: SuggestionResult) -> SuggestionResult:
        client = get_openai_client()
        if client is None or not result.content:
            return result
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": result.content},
                ],
                temperature=0.4,
            )
            polished = (response.choices[0].message.content or "").strip()
            if not polished:
                return result
            return result.model_copy(update={"content": polished})
        except Exception:
            return result
