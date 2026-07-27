"""
Thin wrapper around OpenRouter's OpenAI-compatible endpoint.

Model selection: defaults to "openrouter/free", OpenRouter's own
auto-router that picks among currently-available zero-cost models
(so this doesn't go stale as the free-model lineup rotates - see
https://openrouter.ai/models, free tier changes weekly). Falls back
to a hardcoded known-stable free model if the auto-router errors.

NOTE: this environment's network allowlist doesn't include
openrouter.ai, so this client is untested against the live API from
here. Verify with `python -m app.services.llm_client` on your own
machine once LLM_API_KEY is set in backend/.env.
"""

import logging

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Ordered by preference. First is OpenRouter's own auto-router (adapts as
# their free lineup changes). Second is a manual fallback - verified live
# July 2026, but could go stale; check openrouter.ai/models if this errors.
MODEL_CANDIDATES = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete(self, system: str, user: str, models: list[str] | None = None) -> str:
        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Add it to backend/.env (see .env.example)."
            )

        last_error: Exception | None = None
        for model in models or MODEL_CANDIDATES:
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return response.choices[0].message.content
            except Exception as exc:  # noqa: BLE001 - deliberately broad, we fall through
                logger.warning("Model %s failed (%s), trying next candidate", model, exc)
                last_error = exc
                continue

        raise RuntimeError(f"All model candidates failed. Last error: {last_error}")


if __name__ == "__main__":
    # Manual smoke test - run on a machine that can reach openrouter.ai
    logging.basicConfig(level=logging.INFO)
    client = LLMClient()
    print(client.complete("You are terse.", "Say hello in 5 words."))
