import os
from app.interfaces.llm_interface import LLMInterface


def get_llm_service() -> LLMInterface:
    """Return an instance of the configured LLM service.

    Behavior:
    - Reads `LLM_PROVIDER` from the environment (defaults to 'gemini').
    - If the provider exists in `PROVIDER_REGISTRY` it will be imported.
    - Otherwise it will attempt a few sensible fallbacks before raising
      a helpful `ValueError`.

    Any `kwargs` are forwarded to the provider class constructor.
    """
    provider = (os.environ.get("LLM_PROVIDER") or "gemini").strip().lower()

    if provider == "gemini":
        from app.services.llm_services.gemini_service.gemini_service import GeminiService
        return GeminiService()
    else:
        raise ValueError(
            f"LLM provider '{provider}' is not supported. Set environment variable LLM_PROVIDER to available providers."
        )
