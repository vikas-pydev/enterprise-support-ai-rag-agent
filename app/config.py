import os

from dotenv import load_dotenv


load_dotenv()

# LLM provider configuration (defaults work with OmniRoute or any
# OpenAI-compatible gateway — Groq, OpenAI, etc.)
LLM_API_KEY: str = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or ""

if LLM_API_KEY.startswith("gsk_"):
    # Automatic Groq configuration when a Groq API key is supplied
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL") or "https://api.groq.com/openai/v1"
    LLM_MODEL: str = os.getenv("LLM_MODEL") or "openai/gpt-oss-20b"
else:
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    LLM_MODEL: str = os.getenv("LLM_MODEL") or "gpt-4o-mini"

if not LLM_API_KEY:
    if os.getenv("CI") or os.getenv("TESTING") or os.getenv("PYTEST_CURRENT_TEST"):
        LLM_API_KEY = "mock-ci-key-testing"
    else:
        # Graceful fallback: do not crash container startup/healthcheck.
        # Allow Uvicorn to boot so that /health, /docs, and database endpoints function.
        import logging
        logging.getLogger("enterprise_support").warning(
            "WARNING: Neither LLM_API_KEY nor GROQ_API_KEY was found in environment variables. "
            "Server will start in unconfigured mode. Set GROQ_API_KEY in your deployment dashboard."
        )
        LLM_API_KEY = "not-configured"

