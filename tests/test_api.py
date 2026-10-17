import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.schemas import AgentChatResponse
from app.agent import AgentResponse, AgentStep
from app.database.config import DEFAULT_DB_CONFIG
from app.database.connection import ensure_database_exists, test_connection
from app.database.schema import init_db
from app.database.seed import seed_db
from app.database.exceptions import DatabaseError


class TestFastAPIService(unittest.TestCase):
    """Automated integration tests for the FastAPI service layer (Phase 4 & Phase 6)."""

    @classmethod
    def setUpClass(cls):
        """Ensure database is seeded for API read operations if DB is available."""
        cls.client = TestClient(app)
        try:
            from app.vector_store import collection
            from app.ingestion import ingest_directory
            if collection is not None and collection.count() == 0:
                ingest_directory("data/documents", reset=False)
        except Exception:
            pass

        cls.db_available = test_connection(DEFAULT_DB_CONFIG)
        if cls.db_available:
            try:
                ensure_database_exists(DEFAULT_DB_CONFIG)
                init_db(DEFAULT_DB_CONFIG)
                seed_db(DEFAULT_DB_CONFIG)
            except Exception:
                cls.db_available = False

    # -----------------------------------------------------------------
    # 1. System Health & Root Endpoints
    # -----------------------------------------------------------------

    def test_00_root_endpoint(self):
        """Verify GET / returns 200, service metadata, and docs link."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["name"], "Enterprise Support AI Agent API")
        self.assertIn("docs", data)

    def test_01_health_endpoint(self):
        """Verify GET /health returns 200 and healthy status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")

    # -----------------------------------------------------------------
    # 2. RAG Knowledge Base Endpoint
    # -----------------------------------------------------------------

    def test_02_ask_valid_question_with_mocked_llm(self):
        """Verify POST /api/v1/ask integrates retrieval and returns grounded answer and citations."""
        mock_answer = "The domestic meal per diem allowance is $75 per travel day."

        with patch("app.api.main.generate_answer", return_value=mock_answer) as mock_gen:
            payload = {"question": "What is the meal per diem allowance for domestic travel?"}
            response = self.client.post("/api/v1/ask", json=payload)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["question"], payload["question"])
            self.assertEqual(data["answer"], mock_answer)
            self.assertFalse(data["is_refusal"])
            self.assertGreater(len(data["sources"]), 0)

            # Verify citation structure
            first_source = data["sources"][0]
            self.assertIn("rank", first_source)
            self.assertIn("title", first_source)
            self.assertIn("source_file", first_source)
            self.assertIn("chunk_uid", first_source)
            self.assertIn("rerank_score", first_source)
            self.assertIn("snippet", first_source)
            self.assertTrue(mock_gen.called)

    def test_03_ask_empty_question_validation(self):
        """Verify POST /api/v1/ask rejects empty or whitespace-only questions with 422."""
        # Empty string
        res1 = self.client.post("/api/v1/ask", json={"question": ""})
        self.assertEqual(res1.status_code, 422)

        # Whitespace-only string
        res2 = self.client.post("/api/v1/ask", json={"question": "    "})
        self.assertEqual(res2.status_code, 422)

        # Missing field
        res3 = self.client.post("/api/v1/ask", json={})
        self.assertEqual(res3.status_code, 422)

    def test_04_ask_refusal_behavior(self):
        """Verify unanswerable questions produce refusal and empty citations."""
        refusal_text = "I am sorry, but the requested information is not available in the provided documents."

        with patch("app.api.main.generate_answer", return_value=refusal_text):
            payload = {"question": "What is the company pet insurance reimbursement policy?"}
            response = self.client.post("/api/v1/ask", json=payload)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["is_refusal"])
            self.assertEqual(len(data["sources"]), 0)

    # -----------------------------------------------------------------
    # 3. SQL Employee Endpoint
    # -----------------------------------------------------------------

    def test_05_get_employee_found(self):
        """Verify GET /api/v1/employees/{employee_id} returns employee profile and manager."""
        if not self.db_available:
            self.skipTest("PostgreSQL server is not running on localhost:5432")
        response = self.client.get("/api/v1/employees/E1001")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["employee_id"], "E1001")
        self.assertEqual(data["name"], "Alice Chen")
        self.assertEqual(data["department"], "Engineering")
        self.assertEqual(data["job_title"], "Senior Software Engineer")
        self.assertIsNotNone(data["manager"])
        self.assertEqual(data["manager"]["employee_id"], "E1004")
        self.assertEqual(data["manager"]["name"], "David Kim")

    def test_06_get_employee_not_found(self):
        """Verify GET /api/v1/employees/{employee_id} returns 404 for unknown ID."""
        if not self.db_available:
            self.skipTest("PostgreSQL server is not running on localhost:5432")
        response = self.client.get("/api/v1/employees/UNKNOWN_999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("not found", data["detail"].lower())

    # -----------------------------------------------------------------
    # 4. SQL Leave Endpoint
    # -----------------------------------------------------------------

    def test_07_get_leave_summary(self):
        """Verify GET /api/v1/employees/{employee_id}/leave returns leave allocation and balances."""
        if not self.db_available:
            self.skipTest("PostgreSQL server is not running on localhost:5432")
        response = self.client.get("/api/v1/employees/E1001/leave")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["employee_id"], "E1001")
        self.assertEqual(data["name"], "Alice Chen")
        self.assertEqual(data["total_allocated_days"], 34.0)
        self.assertEqual(data["total_used_days"], 10.0)
        self.assertEqual(data["total_remaining_days"], 24.0)
        self.assertGreaterEqual(len(data["balances"]), 2)

    def test_08_get_leave_summary_not_found(self):
        """Verify GET /api/v1/employees/{employee_id}/leave returns 404 for non-existent employee."""
        if not self.db_available:
            self.skipTest("PostgreSQL server is not running on localhost:5432")
        response = self.client.get("/api/v1/employees/UNKNOWN_999/leave")
        self.assertEqual(response.status_code, 404)

    # -----------------------------------------------------------------
    # 5. SQL Travel Endpoint
    # -----------------------------------------------------------------

    def test_09_get_travel_summary(self):
        """Verify GET /api/v1/employees/{employee_id}/travel returns expense rollups and items."""
        if not self.db_available:
            self.skipTest("PostgreSQL server is not running on localhost:5432")
        response = self.client.get("/api/v1/employees/E1001/travel")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["employee_id"], "E1001")
        self.assertEqual(data["total_claims"], 2)
        self.assertEqual(data["total_amount"], 425.0)
        self.assertEqual(data["approved_amount"], 425.0)
        self.assertIn("flights", data["by_category"])
        self.assertIn("meals", data["by_category"])
        self.assertEqual(len(data["expenses"]), 2)

    def test_10_get_travel_summary_not_found(self):
        """Verify GET /api/v1/employees/{employee_id}/travel returns 404 for non-existent employee."""
        if not self.db_available:
            self.skipTest("PostgreSQL server is not running on localhost:5432")
        response = self.client.get("/api/v1/employees/UNKNOWN_999/travel")
        self.assertEqual(response.status_code, 404)

    # -----------------------------------------------------------------
    # 6. Error Sanitization & Security
    # -----------------------------------------------------------------

    def test_11_database_error_handling_sanitization(self):
        """Verify DatabaseError triggers 500 response without leaking credentials or stack traces."""
        with patch("app.api.main.get_employee_summary", side_effect=DatabaseError("Simulated connection timeout")):
            response = self.client.get("/api/v1/employees/E1001")
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn("error_type", data)
            self.assertEqual(data["error_type"], "DatabaseError")
            self.assertNotIn("password", response.text.lower())
            self.assertNotIn("postgresql://", response.text.lower())

    # -----------------------------------------------------------------
    # 7. Agent Conversational Endpoint (Phase 6)
    # -----------------------------------------------------------------

    def test_12_agent_chat_endpoint_success(self):
        """Verify POST /api/v1/agent/chat processes request and returns AgentChatResponse."""
        mock_resp = AgentResponse(
            session_id="session_api_test",
            query="Tell me about E1001",
            final_answer="Alice Chen is a Senior Software Engineer.",
            steps=[AgentStep(tool_name="get_employee", tool_args={"employee_id": "E1001"}, tool_result={"found": True})],
            total_steps=1,
            status="completed",
            citations=[],
        )

        with patch("app.api.main.run_agent", return_value=mock_resp):
            payload = {"session_id": "session_api_test", "message": "Tell me about E1001"}
            response = self.client.post("/api/v1/agent/chat", json=payload)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["session_id"], "session_api_test")
            self.assertEqual(data["answer"], "Alice Chen is a Senior Software Engineer.")
            self.assertEqual(data["total_steps"], 1)

    def test_13_agent_chat_validation_errors(self):
        """Verify POST /api/v1/agent/chat returns 422 on invalid message or session_id."""
        # Empty message
        res1 = self.client.post("/api/v1/agent/chat", json={"session_id": "s1", "message": ""})
        self.assertEqual(res1.status_code, 422)

        # Empty session_id
        res2 = self.client.post("/api/v1/agent/chat", json={"session_id": "", "message": "hello"})
        self.assertEqual(res2.status_code, 422)

    def test_14_agent_session_clear_and_delete(self):
        """Verify session clear and delete endpoints return proper confirmation schemas."""
        res_clear = self.client.post("/api/v1/agent/sessions/test_sess_clear_api/clear")
        self.assertEqual(res_clear.status_code, 200)
        self.assertEqual(res_clear.json()["status"], "cleared")

        res_delete = self.client.delete("/api/v1/agent/sessions/test_sess_delete_api")
        self.assertEqual(res_delete.status_code, 200)
        self.assertEqual(res_delete.json()["status"], "deleted")

    # -----------------------------------------------------------------
    # 8. Human-in-the-Loop Approval Decision Endpoint (Phase 7 Task 4)
    # -----------------------------------------------------------------

    def test_15_approval_decision_endpoint_invalid_decision(self):
        """Verify POST /api/v1/agent/approvals/{approval_id} rejects invalid decisions."""
        payload = {"decision": "maybe", "reason": "Not sure"}
        response = self.client.post("/api/v1/agent/approvals/appr-test-123", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_16_approval_decision_endpoint_unknown_id(self):
        """Verify POST /api/v1/agent/approvals/{approval_id} returns 404 for unknown approval."""
        payload = {"decision": "approve", "reason": "Manager approved"}
        response = self.client.post("/api/v1/agent/approvals/appr-non-existent-999", json=payload)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("not found", data["detail"].lower())


if __name__ == "__main__":
    unittest.main()
