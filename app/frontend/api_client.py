"""Frontend API Client Layer for Enterprise Support AI Agent.

Provides an encapsulated, robust HTTP client connecting the Streamlit UI to
the FastAPI backend service layer. Manages request lifecycle, timeouts, connection
failures, and status code translations with sanitized user-facing error reporting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
import requests

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 45.0
HEALTH_CHECK_TIMEOUT_SECONDS = 3.0


class ApiClientError(Exception):
    """Base exception for frontend API client errors."""


class ApiConnectionError(ApiClientError):
    """Raised when the backend server is unreachable or offline."""


@dataclass
class ApiResponse:
    """Standardized response object returned by the ApiClient."""

    success: bool
    data: dict[str, Any] | list[Any] | None = None
    error: str | None = None
    error_type: str | None = None
    status_code: int | None = None
    raw: requests.Response | None = field(default=None, repr=False)

    @property
    def is_ok(self) -> bool:
        """Returns True if the request succeeded and returned valid data."""
        return self.success and self.error is None


class ApiClient:
    """Client for interacting with the Enterprise Support AI Agent FastAPI backend."""

    def __init__(
        self,
        base_url: str = DEFAULT_BACKEND_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "EnterpriseSupportAgent-Streamlit/1.0",
            }
        )

    def _format_url(self, endpoint: str) -> str:
        """Constructs a clean URL for the given endpoint."""
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}"

    def _handle_request(
        self,
        method: str,
        endpoint: str,
        json_payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ApiResponse:
        """Executes an HTTP request with comprehensive error trapping and sanitization."""
        url = self._format_url(endpoint)
        req_timeout = timeout or self.timeout

        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                json=json_payload,
                timeout=req_timeout,
            )

            # 2xx Success
            if 200 <= response.status_code < 300:
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text}
                return ApiResponse(
                    success=True,
                    data=data,
                    status_code=response.status_code,
                    raw=response,
                )

            # 4xx / 5xx Error handling
            error_detail = "An error occurred while processing the request."
            error_type = "HttpError"

            try:
                err_json = response.json()
                if isinstance(err_json, dict):
                    if "detail" in err_json:
                        detail_val = err_json["detail"]
                        if isinstance(detail_val, list):
                            # FastAPI 422 validation error structure
                            messages = [f"{item.get('loc', ['field'])[-1]}: {item.get('msg', '')}" for item in detail_val if isinstance(item, dict)]
                            error_detail = "Validation Error: " + "; ".join(messages)
                        else:
                            error_detail = str(detail_val)
                    elif "message" in err_json:
                        error_detail = str(err_json["message"])
                    error_type = err_json.get("error_type", "HttpError")
            except Exception:
                error_detail = f"Server returned HTTP {response.status_code}: {response.reason}"

            logger.warning(
                "API call returned non-2xx: %s %s -> %d (%s)",
                method,
                url,
                response.status_code,
                error_detail,
            )

            return ApiResponse(
                success=False,
                error=error_detail,
                error_type=error_type,
                status_code=response.status_code,
                raw=response,
            )

        except requests.exceptions.ConnectionError:
            logger.warning("Failed to connect to backend at %s", url)
            return ApiResponse(
                success=False,
                error=(
                    f"Unable to connect to the backend server at {self.base_url}. "
                    "Please ensure the FastAPI service is running (`uvicorn app.api.main:app --reload`)."
                ),
                error_type="ConnectionError",
                status_code=None,
            )
        except requests.exceptions.Timeout:
            logger.warning("Request timed out to %s (timeout=%.1fs)", url, req_timeout)
            return ApiResponse(
                success=False,
                error=(
                    f"The request timed out after {req_timeout:.1f} seconds. "
                    "The backend model or retrieval pipeline may be processing a heavy workload."
                ),
                error_type="TimeoutError",
                status_code=None,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Unexpected requests error during %s %s: %s", method, url, e)
            return ApiResponse(
                success=False,
                error="A network communication error occurred with the AI agent backend.",
                error_type="NetworkError",
                status_code=None,
            )
        except Exception as e:
            logger.error("Unhandled client exception: %s", e, exc_info=True)
            return ApiResponse(
                success=False,
                error="An internal client error occurred while preparing the request.",
                error_type="ClientError",
                status_code=None,
            )

    # -----------------------------------------------------------------
    # 1. System Health
    # -----------------------------------------------------------------

    def check_health(self) -> ApiResponse:
        """Queries the GET /health service status endpoint."""
        return self._handle_request(
            method="GET",
            endpoint="/health",
            timeout=HEALTH_CHECK_TIMEOUT_SECONDS,
        )

    # -----------------------------------------------------------------
    # 2. Policy Assistant (RAG)
    # -----------------------------------------------------------------

    def ask_policy(self, question: str) -> ApiResponse:
        """Submits a policy question to the POST /api/v1/ask endpoint."""
        clean_question = question.strip() if question else ""
        if not clean_question:
            return ApiResponse(
                success=False,
                error="Please enter a non-empty policy question.",
                error_type="ValidationError",
                status_code=422,
            )

        return self._handle_request(
            method="POST",
            endpoint="/api/v1/ask",
            json_payload={"question": clean_question},
        )

    # -----------------------------------------------------------------
    # 3. AI Agent (Multi-Turn Chat & Tool Orchestration)
    # -----------------------------------------------------------------

    def chat_agent(self, message: str, session_id: str) -> ApiResponse:
        """Sends a multi-turn message to the conversational AI agent via POST /api/v1/agent/chat."""
        clean_msg = message.strip() if message else ""
        clean_sid = session_id.strip() if session_id else ""

        if not clean_msg:
            return ApiResponse(
                success=False,
                error="Please enter a non-empty message for the agent.",
                error_type="ValidationError",
                status_code=422,
            )
        if not clean_sid:
            return ApiResponse(
                success=False,
                error="A valid session identifier is required for agent conversation.",
                error_type="ValidationError",
                status_code=422,
            )

        return self._handle_request(
            method="POST",
            endpoint="/api/v1/agent/chat",
            json_payload={"session_id": clean_sid, "message": clean_msg},
        )

    # -----------------------------------------------------------------
    # 4. Session History Management
    # -----------------------------------------------------------------

    def clear_session(self, session_id: str) -> ApiResponse:
        """Clears conversational context via POST /api/v1/agent/sessions/{session_id}/clear."""
        clean_sid = session_id.strip() if session_id else ""
        if not clean_sid:
            return ApiResponse(
                success=False,
                error="A valid session identifier is required.",
                error_type="ValidationError",
                status_code=422,
            )

        return self._handle_request(
            method="POST",
            endpoint=f"/api/v1/agent/sessions/{clean_sid}/clear",
        )

    def delete_session(self, session_id: str) -> ApiResponse:
        """Deletes a session and durable checkpoints via DELETE /api/v1/agent/sessions/{session_id}."""
        clean_sid = session_id.strip() if session_id else ""
        if not clean_sid:
            return ApiResponse(
                success=False,
                error="A valid session identifier is required.",
                error_type="ValidationError",
                status_code=422,
            )

        return self._handle_request(
            method="DELETE",
            endpoint=f"/api/v1/agent/sessions/{clean_sid}",
        )

    # -----------------------------------------------------------------
    # 5. Human-in-the-Loop Approval Resumption
    # -----------------------------------------------------------------

    def submit_approval(
        self,
        approval_id: str,
        decision: str,
        notes: str | None = None,
    ) -> ApiResponse:
        """Submits human approval decision via POST /api/v1/agent/approvals/{approval_id}."""
        clean_appr_id = approval_id.strip() if approval_id else ""
        clean_decision = decision.strip().lower() if decision else ""

        if not clean_appr_id:
            return ApiResponse(
                success=False,
                error="A valid approval identifier is required.",
                error_type="ValidationError",
                status_code=422,
            )
        if clean_decision not in ("approve", "reject"):
            return ApiResponse(
                success=False,
                error="Decision must be explicitly 'approve' or 'reject'.",
                error_type="ValidationError",
                status_code=422,
            )

        payload: dict[str, Any] = {"decision": clean_decision}
        if notes:
            payload["notes"] = notes.strip()

        return self._handle_request(
            method="POST",
            endpoint=f"/api/v1/agent/approvals/{clean_appr_id}",
            json_payload=payload,
        )

    # -----------------------------------------------------------------
    # 6. Structured Enterprise Data Lookups (Direct Helper Endpoints)
    # -----------------------------------------------------------------

    def get_employee(self, employee_id: str) -> ApiResponse:
        """Fetches employee profile via GET /api/v1/employees/{employee_id}."""
        clean_id = employee_id.strip() if employee_id else ""
        return self._handle_request(
            method="GET",
            endpoint=f"/api/v1/employees/{clean_id}",
        )

    def get_employee_leave(self, employee_id: str) -> ApiResponse:
        """Fetches employee PTO balance via GET /api/v1/employees/{employee_id}/leave."""
        clean_id = employee_id.strip() if employee_id else ""
        return self._handle_request(
            method="GET",
            endpoint=f"/api/v1/employees/{clean_id}/leave",
        )

    def get_employee_travel(self, employee_id: str) -> ApiResponse:
        """Fetches employee travel expense summary via GET /api/v1/employees/{employee_id}/travel."""
        clean_id = employee_id.strip() if employee_id else ""
        return self._handle_request(
            method="GET",
            endpoint=f"/api/v1/employees/{clean_id}/travel",
        )
