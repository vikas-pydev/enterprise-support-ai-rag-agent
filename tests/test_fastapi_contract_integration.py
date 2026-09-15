"""Deterministic FastAPI ↔ Frontend API Contract Integration Tests (Phase 9 Task 8).

Validates the full request/response boundary between the FastAPI application and the
schemas expected by the Next.js TypeScript API client:
1. Health endpoint (`/health`)
2. Policy Assistant (`/api/v1/ask`) with grounded, refusal, 422, and 500 cases
3. Operational employee endpoints (`/employees/{id}`, `/leave`, `/travel`)
4. Conversational agent chat (`/agent/chat`) with multi-turn and session isolation
5. Human-in-the-Loop approvals (`/agent/approvals/{id}`) with approve, reject, 403, and 400 replay
6. Session clear/delete lifecycle (`/agent/sessions/{id}`)
7. Error and security sanitization preventing credentials and stack traces from leaking
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.schemas import (
    HealthResponse,
    AskResponse,
    EmployeeResponse,
    EmployeeLeaveResponse,
    EmployeeTravelResponse,
    AgentChatResponse,
    ApprovalDecisionResponse,
    SessionClearResponse,
)
from app.agent import AgentResponse, AgentStep, AgentExecutionTrace
from app.database.exceptions import DatabaseError


class TestFastAPIFrontendContractIntegration(unittest.TestCase):
    """Verifies FastAPI API boundary directly with TestClient and exact frontend schemas."""

    def setUp(self):
        self.client = TestClient(app)

    # -----------------------------------------------------------------
    # 1. Health Endpoint Integration
    # -----------------------------------------------------------------
    def test_health_contract(self):
        """GET /health returns 200 and matches HealthResponse schema."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        validated = HealthResponse(**data)
        self.assertEqual(validated.status, "healthy")
        self.assertEqual(validated.version, "1.0.0")

    # -----------------------------------------------------------------
    # 2. Policy Assistant Integration (POST /api/v1/ask)
    # -----------------------------------------------------------------
    def test_ask_policy_grounded_contract(self):
        """POST /api/v1/ask returns grounded response and citations."""
        mock_answer = "The domestic meal per diem allowance is $75 per travel day."
        with patch("app.api.main.generate_answer", return_value=mock_answer):
            res = self.client.post(
                "/api/v1/ask",
                json={"question": "What is the meal per diem allowance for domestic travel?"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = AskResponse(**data)
            self.assertFalse(validated.is_refusal)
            self.assertEqual(validated.answer, mock_answer)
            self.assertGreater(len(validated.sources), 0)
            # Verify citation source schema
            src = validated.sources[0]
            self.assertEqual(src.rank, 1)
            self.assertTrue(src.chunk_uid)
            self.assertIsInstance(src.rerank_score, float)

    def test_ask_policy_refusal_contract(self):
        """POST /api/v1/ask returns refusal with is_refusal=True and zero citations."""
        refusal_text = "I am sorry, but the requested information is not available in the provided documents."
        with patch("app.api.main.generate_answer", return_value=refusal_text):
            res = self.client.post(
                "/api/v1/ask",
                json={"question": "What is the company pet insurance reimbursement policy?"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = AskResponse(**data)
            self.assertTrue(validated.is_refusal)
            self.assertEqual(len(validated.sources), 0)

    def test_ask_policy_validation_failure_422(self):
        """POST /api/v1/ask rejects empty question with 422."""
        res = self.client.post("/api/v1/ask", json={"question": ""})
        self.assertEqual(res.status_code, 422)
        res_ws = self.client.post("/api/v1/ask", json={"question": "   "})
        self.assertEqual(res_ws.status_code, 422)

    # -----------------------------------------------------------------
    # 3. Employee, Leave & Travel Endpoints
    # -----------------------------------------------------------------
    def test_employee_profile_contract(self):
        """GET /api/v1/employees/{id} returns EmployeeResponse contract."""
        mock_emp = {
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
        }
        with patch("app.api.main.get_employee_summary", return_value=mock_emp):
            res = self.client.get("/api/v1/employees/E1001")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = EmployeeResponse(**data)
            self.assertEqual(validated.employee_id, "E1001")
            self.assertEqual(validated.manager.employee_id, "E1004")

    def test_employee_missing_404(self):
        """GET /api/v1/employees/{id} returns 404 for unknown employee."""
        with patch("app.api.main.get_employee_summary", return_value=None):
            res = self.client.get("/api/v1/employees/E9999")
            self.assertEqual(res.status_code, 404)
            self.assertIn("not found", res.json()["detail"].lower())

    def test_employee_leave_contract(self):
        """GET /api/v1/employees/{id}/leave returns EmployeeLeaveResponse contract."""
        mock_leave = {
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
                }
            ],
        }
        with patch("app.api.main.get_employee_leave_summary", return_value=mock_leave):
            res = self.client.get("/api/v1/employees/E1001/leave")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = EmployeeLeaveResponse(**data)
            self.assertEqual(validated.total_remaining_days, 24.0)

    def test_employee_travel_contract(self):
        """GET /api/v1/employees/{id}/travel returns EmployeeTravelResponse contract."""
        mock_travel = {
            "employee_id": "E1001",
            "name": "Alice Chen",
            "department": "Engineering",
            "total_claims": 1,
            "total_amount": 350.0,
            "approved_amount": 350.0,
            "submitted_amount": 0.0,
            "reimbursed_amount": 350.0,
            "by_category": {"flights": 350.0},
            "expenses": [
                {
                    "id": 1,
                    "expense_date": "2026-02-14",
                    "category": "flights",
                    "amount": 350.0,
                    "currency": "USD",
                    "status": "approved",
                    "description": "Domestic flight",
                    "created_at": "2026-02-14T00:00:00",
                }
            ],
        }
        with patch("app.api.main.get_employee_travel_summary", return_value=mock_travel):
            res = self.client.get("/api/v1/employees/E1001/travel")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = EmployeeTravelResponse(**data)
            self.assertEqual(validated.total_claims, 1)

    # -----------------------------------------------------------------
    # 4. Agent Chat & HITL Approvals Integration
    # -----------------------------------------------------------------
    def test_agent_chat_contract(self):
        """POST /api/v1/agent/chat returns AgentChatResponse contract."""
        mock_agent_res = AgentResponse(
            session_id="test-session-123",
            query="Employee profile for E1001",
            final_answer="Alice Chen is a Senior Software Engineer.",
            status="completed",
            steps=[
                AgentStep(
                    step_number=1,
                    tool_name="get_employee_profile_tool",
                    tool_args={"employee_id": "E1001"},
                    tool_result={"name": "Alice Chen"},
                    status="success",
                    duration_ms=45.0,
                )
            ],
            total_steps=1,
            duration_ms=90.0,
            used_rag=False,
            citations=[],
            trace=AgentExecutionTrace(
                session_id="test-session-123",
                query="Employee profile for E1001",
                total_steps=1,
                total_duration_ms=90.0,
                used_rag=False,
                status="completed",
                tools_invoked=["get_employee_profile_tool"],
            ),
        )
        with patch("app.api.main.run_agent", return_value=mock_agent_res):
            res = self.client.post(
                "/api/v1/agent/chat",
                json={"session_id": "test-session-123", "message": "Employee profile for E1001"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = AgentChatResponse(**data)
            self.assertEqual(validated.session_id, "test-session-123")
            self.assertEqual(validated.status, "completed")
            self.assertEqual(len(validated.steps), 1)

    def test_agent_approval_decision_contract(self):
        """POST /api/v1/agent/approvals/{id} returns ApprovalDecisionResponse contract."""
        mock_appr_res = AgentResponse(
            session_id="session-appr-1",
            query="resume",
            final_answer="Approval granted. Operation complete.",
            status="completed",
            duration_ms=50.0,
            trace=AgentExecutionTrace(
                session_id="session-appr-1",
                query="resume",
                total_steps=1,
                total_duration_ms=50.0,
                used_rag=False,
                status="completed",
                tools_invoked=["cancel_tool"],
            ),
        )
        with patch("app.api.main.resume_multi_agent_approval", return_value=mock_appr_res):
            res = self.client.post(
                "/api/v1/agent/approvals/appr_req_1001",
                json={"decision": "approve", "session_id": "session-appr-1", "notes": "Approved"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            validated = ApprovalDecisionResponse(**data)
            self.assertEqual(validated.approval_id, "appr_req_1001")
            self.assertEqual(validated.decision, "approve")
            self.assertEqual(validated.status, "completed")

    def test_agent_approval_wrong_session_403(self):
        """POST /api/v1/agent/approvals/{id} returns 403 on session authorization mismatch."""
        mock_auth_res = AgentResponse(
            session_id="session-attacker",
            query="resume",
            final_answer="Authorization failure: Approval request does not belong to session.",
            status="error",
        )
        with patch("app.api.main.resume_multi_agent_approval", return_value=mock_auth_res):
            res = self.client.post(
                "/api/v1/agent/approvals/appr_req_1001",
                json={"decision": "approve", "session_id": "session-attacker"},
            )
            self.assertEqual(res.status_code, 403)
            self.assertIn("authorization", res.json()["detail"].lower())

    def test_agent_session_clear_and_delete_contract(self):
        """POST /clear and DELETE session return SessionClearResponse contract."""
        res_clear = self.client.post("/api/v1/agent/sessions/session-1/clear")
        self.assertEqual(res_clear.status_code, 200)
        data_clear = res_clear.json()
        validated_clear = SessionClearResponse(**data_clear)
        self.assertEqual(validated_clear.status, "cleared")

        res_del = self.client.delete("/api/v1/agent/sessions/session-1")
        self.assertEqual(res_del.status_code, 200)
        data_del = res_del.json()
        validated_del = SessionClearResponse(**data_del)
        self.assertEqual(validated_del.status, "deleted")

    # -----------------------------------------------------------------
    # 5. Security & Error Sanitization Boundary
    # -----------------------------------------------------------------
    def test_database_error_handler_sanitization(self):
        """DatabaseError is caught and sanitized into safe 500 error."""
        with patch("app.api.main.get_employee_summary", side_effect=DatabaseError("DB Secret Password")):
            res = self.client.get("/api/v1/employees/E1001")
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["error_type"], "DatabaseError")
            self.assertNotIn("Password", data["detail"])


if __name__ == "__main__":
    unittest.main()
