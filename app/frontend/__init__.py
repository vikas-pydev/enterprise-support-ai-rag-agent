"""Frontend package for the Enterprise Support AI Agent Streamlit application.

Provides a clean API client helper layer connecting the Streamlit UI to the
FastAPI service layer.
"""

from app.frontend.api_client import (
    ApiClient,
    ApiClientError,
    ApiConnectionError,
    ApiResponse,
)

__all__ = [
    "ApiClient",
    "ApiClientError",
    "ApiConnectionError",
    "ApiResponse",
]
