from openai import OpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)


def ask_llm(messages: list[dict]) -> str:
    """Single grounded completion through the configured LLM provider.

    Uses the Chat Completions API (universally supported by OpenAI-compatible
    gateways) rather than the Responses API.
    """
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
    )

    return response.choices[0].message.content or ""