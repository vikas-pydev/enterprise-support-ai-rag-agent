"""Deterministic FastAPI Integration Server for Next.js Frontend ↔ Backend Integration Testing.

Runs a real uvicorn FastAPI server on an ephemeral or configured port with deterministic
mocked backend boundaries (no external Groq LLM or live PostgreSQL database required).

Exercises real FastAPI routing, Pydantic validation, serialization, CORS headers,
and global exception handling.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock, patch

# Pre-mock heavy ML modules so test server boots deterministically in seconds
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["app.reranker"] = MagicMock()
sys.modules["app.embeddings"] = MagicMock()

import uvicorn
from app.api.main import app
from app.api.schemas import CitationSource
from app.agent import AgentResponse, AgentStep, AgentExecutionTrace
from app.database.exceptions import DatabaseError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("integration_server")

# In-memory test state
TEST_SESSIONS = {}
TEST_APPROVALS = {
    "appr_req_1001": {
        "approval_id": "appr_req_1001",
        "session_id": "session_test_approval",
        "status": "pending",
        "reason": "Cancelling travel expense claims for E1001 requires executive sign-off.",
        "target_worker": "travel_coordinator",
    }
}

MOCK_EMPLOYEES = {
    "E1001": {
        "employee_id": "E1001",
        "name": "Alice Chen",
        "email": "alice.chen@enterprise.internal",
        "department": "Engineering",
        "job_title": "Senior Software Engineer",
        "created_at": "2026-01-01T00:00:00",
        "manager": {
            "employee_id": "E1004",
            "name": "David Kim",
            "email": "david.kim@enterprise.internal",
            "job_title": "VP of Operations",
        },
    },
    "E1002": {
        "employee_id": "E1002",
        "name": "Bob Martinez",
        "email": "bob.martinez@enterprise.internal",
        "department": "Marketing",
        "job_title": "Growth Marketing Manager",
        "created_at": "2026-01-01T00:00:00",
        "manager": {
            "employee_id": "E1004",
            "name": "David Kim",
            "email": "david.kim@enterprise.internal",
            "job_title": "VP of Operations",
        },
    },
}

MOCK_LEAVE = {
    "E1001": {
        "employee_id": "E1001",
        "name": "Alice Chen",
        "department": "Engineering",
        "total_allocated_days": 34.0,
        "total_used_days": 10.0,
        "total_remaining_days": 24.0,
        "balances": [
            {
                "leave_type": "annual",
                "total_days": 24.0,
                "used_days": 8.0,
                "remaining_days": 16.0,
                "updated_at": "2026-01-01T00:00:00",
            },
            {
                "leave_type": "sick",
                "total_days": 10.0,
                "used_days": 2.0,
                "remaining_days": 8.0,
                "updated_at": "2026-01-01T00:00:00",
            },
        ],
    },
}

MOCK_TRAVEL = {
    "E1001": {
        "employee_id": "E1001",
        "name": "Alice Chen",
        "department": "Engineering",
        "total_claims": 2,
        "total_amount": 425.0,
        "approved_amount": 425.0,
        "submitted_amount": 0.0,
        "reimbursed_amount": 425.0,
        "by_category": {"flights": 350.0, "meals": 75.0},
        "expenses": [
            {
                "id": 1,
                "expense_date": "2026-02-14",
                "category": "flights",
                "amount": 350.0,
                "currency": "USD",
                "status": "approved",
                "description": "Domestic flight to Seattle for architecture review",
                "created_at": "2026-02-14T00:00:00",
            },
            {
                "id": 2,
                "expense_date": "2026-02-15",
                "category": "meals",
                "amount": 75.0,
                "currency": "USD",
                "status": "approved",
                "description": "Client working dinner in Seattle",
                "created_at": "2026-02-15T00:00:00",
            },
        ],
    },
}


# =====================================================================
# DETERMINISTIC MOCK HANDLERS
# =====================================================================

def mock_retrieve(query, config=None, return_stats=True):
    q_lower = query.lower()
    if "pet insurance" in q_lower or "unanswerable" in q_lower:
        return [], type("Stats", (), {"initial_chunks": 0, "final_chunks": 0})()

    if "trigger_500" in q_lower or "internal_error" in q_lower:
        raise RuntimeError("Simulated internal retrieval failure")

    results = [
        (
            "Section 3.2 Meal Per Diem: Domestic travel allows up to $75 per day for business meals.",
            0.945,
            {
                "title": "Corporate Travel & Expense Policy",
                "source": "data/policies/travel_policy.md",
                "chunk_uid": "travel_chunk_1",
                "rerank_score": 0.945,
            },
        )
    ]
    stats = type("Stats", (), {"initial_chunks": 5, "final_chunks": 1})()
    return results, stats


def mock_generate_answer(question, contexts):
    q_lower = question.lower()
    if not contexts or "pet insurance" in q_lower or "unanswerable" in q_lower:
        return "I am sorry, but the requested information is not available in the provided documents."
    if "trigger_500" in q_lower:
        raise RuntimeError("Simulated internal LLM generator failure")
    return "The domestic meal per diem allowance is $75 per travel day according to Section 3.2 of the Corporate Travel Policy."


def mock_get_employee_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    if clean == "trigger_db_error":
        raise DatabaseError("Simulated database operational connection failure")
    return MOCK_EMPLOYEES.get(clean)


def mock_get_employee_leave_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    if clean == "trigger_db_error":
        raise DatabaseError("Simulated database operational connection failure")
    return MOCK_LEAVE.get(clean)


def mock_get_employee_travel_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    if clean == "trigger_db_error":
        raise DatabaseError("Simulated database operational connection failure")
    return MOCK_TRAVEL.get(clean)


def mock_run_agent(user_query: str, session_id: str):
    q_lower = user_query.lower()

    if "trigger_agent_error" in q_lower:
        raise RuntimeError("Simulated agent unhandled failure")

    if "trigger_db_error" in q_lower:
        raise DatabaseError("Simulated database failure during agent execution")

    # Session history tracking
    history = TEST_SESSIONS.setdefault(session_id, [])
    history.append(user_query)

    # Pending approval query
    if "cancel" in q_lower and "travel" in q_lower:
        appr_id = "appr_req_1001"
        TEST_APPROVALS[appr_id] = {
            "approval_id": appr_id,
            "session_id": session_id,
            "status": "pending",
            "reason": "Cancelling travel expense claims for E1001 requires executive sign-off.",
            "target_worker": "travel_coordinator",
        }
        return AgentResponse(
            session_id=session_id,
            query=user_query,
            final_answer="Action paused: cancelling travel expense claims requires manager approval.",
            status="pending_approval",
            steps=[
                AgentStep(
                    step_number=1,
                    tool_name="request_approval_tool",
                    tool_args={"action": "cancel_travel_claims", "employee_id": "E1001"},
                    tool_result={"approval_id": appr_id, "status": "pending"},
                    status="success",
                    duration_ms=25.0,
                )
            ],
            total_steps=1,
            duration_ms=65.0,
            used_rag=False,
            citations=[],
            trace=AgentExecutionTrace(
                session_id=session_id,
                query=user_query,
                total_steps=1,
                total_duration_ms=65.0,
                used_rag=False,
                status="pending_approval",
                tools_invoked=["request_approval_tool"],
            ),
        )

    # Multi-turn follow up: if history has 2 messages, demonstrate context continuity
    if len(history) > 1 and ("leave" in q_lower or "balance" in q_lower or "her" in q_lower or "she" in q_lower):
        return AgentResponse(
            session_id=session_id,
            query=user_query,
            final_answer="Alice Chen has 24 remaining PTO days (16 annual, 8 sick).",
            status="completed",
            steps=[
                AgentStep(
                    step_number=1,
                    tool_name="get_employee_leave_tool",
                    tool_args={"employee_id": "E1001"},
                    tool_result={"remaining_days": 24.0, "balances": [{"leave_type": "annual", "remaining_days": 16.0}]},
                    status="success",
                    duration_ms=30.0,
                )
            ],
            total_steps=1,
            duration_ms=55.0,
            used_rag=False,
            citations=[],
            trace=AgentExecutionTrace(
                session_id=session_id,
                query=user_query,
                total_steps=1,
                total_duration_ms=55.0,
                used_rag=False,
                status="completed",
                tools_invoked=["get_employee_leave_tool"],
            ),
        )

    # Standard turn 1 response
    return AgentResponse(
        session_id=session_id,
        query=user_query,
        final_answer="Alice Chen is a Senior Software Engineer in the Engineering department.",
        status="completed",
        steps=[
            AgentStep(
                step_number=1,
                tool_name="get_employee_profile_tool",
                tool_args={"employee_id": "E1001"},
                tool_result={"name": "Alice Chen", "department": "Engineering"},
                status="success",
                duration_ms=45.0,
            )
        ],
        total_steps=1,
        duration_ms=90.0,
        used_rag=False,
        citations=[
            {
                "rank": 1,
                "title": "Employee Directory",
                "source_file": "data/employees.sql",
                "chunk_uid": "emp_1001",
                "rerank_score": 1.0,
                "snippet": "Alice Chen - Engineering",
            }
        ],
        trace=AgentExecutionTrace(
            session_id=session_id,
            query=user_query,
            total_steps=1,
            total_duration_ms=90.0,
            used_rag=False,
            status="completed",
            tools_invoked=["get_employee_profile_tool"],
        ),
    )


def mock_resume_multi_agent_approval(approval_id: str, decision: str, expected_session_id: str | None = None):
    appr = TEST_APPROVALS.get(approval_id)
    if not appr:
        return AgentResponse(
            session_id=expected_session_id,
            query="resume_approval",
            final_answer=f"Approval request '{approval_id}' was not found or has already expired.",
            status="error",
        )

    if expected_session_id and appr["session_id"] != expected_session_id:
        return AgentResponse(
            session_id=expected_session_id,
            query="resume_approval",
            final_answer=f"Authorization failure: Approval request '{approval_id}' does not belong to session '{expected_session_id}'.",
            status="error",
        )

    if appr["status"] != "pending":
        return AgentResponse(
            session_id=appr["session_id"],
            query="resume_approval",
            final_answer=f"Approval request '{approval_id}' is not in a pending state.",
            status="error",
        )

    # Mark as resolved
    appr["status"] = "approved" if decision == "approve" else "rejected"

    if decision == "approve":
        return AgentResponse(
            session_id=appr["session_id"],
            query="resume_approval",
            final_answer="Approval granted: Travel expense claims for E1001 have been cancelled.",
            status="completed",
            duration_ms=40.0,
            trace=AgentExecutionTrace(
                session_id=appr["session_id"],
                query="resume_approval",
                total_steps=1,
                total_duration_ms=40.0,
                used_rag=False,
                status="completed",
                tools_invoked=["cancel_travel_claims_tool"],
            ),
        )
    else:
        return AgentResponse(
            session_id=appr["session_id"],
            query="resume_approval",
            final_answer="Operation cancelled: Operator rejected the approval request.",
            status="rejected",
            duration_ms=20.0,
            trace=AgentExecutionTrace(
                session_id=appr["session_id"],
                query="resume_approval",
                total_steps=0,
                total_duration_ms=20.0,
                used_rag=False,
                status="rejected",
                tools_invoked=[],
            ),
        )


def start_server(host: str = "127.0.0.1", port: int = 8089):
    """Starts uvicorn with patched deterministic handlers."""
    # Apply monkey patches to backend modules for test server lifecycle
    patch("app.api.main.retrieve", side_effect=mock_retrieve).start()
    patch("app.api.main.generate_answer", side_effect=mock_generate_answer).start()
    patch("app.api.main.get_employee_summary", side_effect=mock_get_employee_summary).start()
    patch("app.api.main.get_employee_leave_summary", side_effect=mock_get_employee_leave_summary).start()
    patch("app.api.main.get_employee_travel_summary", side_effect=mock_get_employee_travel_summary).start()
    patch("app.api.main.run_agent", side_effect=mock_run_agent).start()
    patch("app.api.main.resume_multi_agent_approval", side_effect=mock_resume_multi_agent_approval).start()

    logger.info(f"Starting test FastAPI integration server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic FastAPI Integration Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8089, help="Bind port")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port)
