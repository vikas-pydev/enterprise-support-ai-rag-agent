from openai import OpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


client = OpenAI(
    api_key=LLM_API_KEY or "not-configured",
    base_url=LLM_BASE_URL,
)


def ask_llm(messages: list[dict]) -> str:
    """Single grounded completion through the configured LLM provider.

    Uses the Chat Completions API (universally supported by OpenAI-compatible
    gateways) rather than the Responses API.
    """
    if not LLM_API_KEY or LLM_API_KEY in ("not-configured", ""):
        raise ValueError(
            "LLM_API_KEY is not configured. Please set GROQ_API_KEY or LLM_API_KEY in your deployment environment variables."
        )
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
    )

    return response.choices[0].message.content or ""