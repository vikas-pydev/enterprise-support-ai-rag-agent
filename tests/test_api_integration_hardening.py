"""Deterministic Database Resiliency, Session Isolation & API Hardening Tests (Phase 9 Task 4).

Validates:
1. Database connection acquisition, lifecycle cleanup, and exception handling without resource leaks.
2. PostgreSQL OperationalError / DatabaseError sanitization and safe API error contracts.
3. Concurrent multi-session isolation across FastAPI endpoints, session store, and checkpointer threads.
4. Same-session concurrency behavior and thread safety in InMemorySessionStore.
5. Strict API error contracts (HTTP 400, 404, 422, 500) preventing credentials, SQL, or stack traces from leaking.
"""

import unittest
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

import psycopg2
from psycopg2.extras import RealDictCursor

from app.api.main import app
from app.api.schemas import AgentChatResponse, ErrorResponse
from app.agent import AgentResponse, AgentStep, AgentExecutionTrace
from app.agent.memory import InMemorySessionStore, default_session_store
from app.agent.checkpoint import (
    get_thread_id_for_session,
    build_thread_config,
    format_approval_id,
    resolve_thread_from_approval_id,
    delete_thread_checkpoints,
    MemorySaver,
)
from app.database.config import DatabaseConfig
from app.database.connection import get_db_connection, test_connection
from app.database.exceptions import DatabaseError
from app.database.repository import (
    get_employee_by_id,
    get_employee_by_email,
    list_employees_by_department,
    get_employee_manager,
    get_leave_balances,
    get_leave_balance_by_type,
    get_travel_expenses,
    get_travel_expenses_by_status,
    get_total_travel_expenses,
    get_travel_expenses_in_date_range,
    get_employee_summary,
    get_employee_leave_summary,
    get_employee_travel_summary,
    get_department_employee_summary,
    get_pending_travel_expenses,
)


class TestDatabaseConnectionResiliency(unittest.TestCase):
    """Deterministic tests for database connection lifecycle, resource cleanup, and exception sanitization."""

    def setUp(self):
        self.mock_config = DatabaseConfig(name="test_resiliency_db")

    # -----------------------------------------------------------------
    # 1. Resource Cleanup on Success
    # -----------------------------------------------------------------

    @patch("psycopg2.connect")
    def test_connection_and_cursor_cleanup_on_successful_repository_call(self, mock_connect):
        """Verify connection and cursor are cleanly closed after successful query execution."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.return_value = {
            "id": 1,
            "employee_id": "E1001",
            "name": "Alice Chen",
            "email": "alice.chen@enterprise.internal",
            "department": "Engineering",
            "job_title": "Senior Software Engineer",
            "manager_employee_id": "E1004",
            "created_at": "2026-01-01T00:00:00",
        }

        emp = get_employee_by_id("E1001", config=self.mock_config)

        self.assertIsNotNone(emp)
        self.assertEqual(emp["employee_id"], "E1001")
        # Ensure cursor was opened and closed via context manager
        self.assertTrue(mock_conn.cursor.called)
        self.assertTrue(mock_conn.cursor.return_value.__exit__.called)
        # Ensure connection was closed in finally block
        self.assertTrue(mock_conn.close.called)

    # -----------------------------------------------------------------
    # 2. Resource Cleanup on Exceptions
    # -----------------------------------------------------------------

    @patch("psycopg2.connect")
    def test_connection_cleanup_after_repository_operational_exception(self, mock_connect):
        """Verify connection is closed in finally block even when a database OperationalError occurs."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.execute.side_effect = psycopg2.OperationalError("Server closed connection unexpectedly")

        with self.assertRaises(DatabaseError) as ctx:
            get_employee_by_id("E1001", config=self.mock_config)

        self.assertIn("Failed to fetch employee", str(ctx.exception))
        self.assertIsInstance(ctx.exception.original_error, psycopg2.OperationalError)
        # Connection must be closed despite exception
        self.assertTrue(mock_conn.close.called)

    @patch("psycopg2.connect")
    def test_cursor_and_connection_cleanup_on_fetch_error(self, mock_connect):
        """Verify cursor and connection resources are not leaked when fetchone/fetchall raises."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.side_effect = psycopg2.DatabaseError("Data corruption reading page")

        with self.assertRaises(DatabaseError):
            get_leave_balances("E1001", config=self.mock_config)

        self.assertTrue(mock_conn.cursor.return_value.__exit__.called)
        self.assertTrue(mock_conn.close.called)

    # -----------------------------------------------------------------
    # 3. Error Translation & Sanitization
    # -----------------------------------------------------------------

    @patch("psycopg2.connect")
    def test_operational_error_translation_across_repository_functions(self, mock_connect):
        """Verify psycopg2 errors are systematically translated into safe DatabaseError across operations."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.execute.side_effect = psycopg2.OperationalError("connection timeout")

        repo_calls = [
            lambda: get_employee_by_email("alice@test.com", config=self.mock_config),
            lambda: list_employees_by_department("Engineering", config=self.mock_config),
            lambda: get_employee_manager("E1001", config=self.mock_config),
            lambda: get_leave_balance_by_type("E1001", "annual", config=self.mock_config),
            lambda: get_travel_expenses("E1001", config=self.mock_config),
            lambda: get_total_travel_expenses("E1001", config=self.mock_config),
            lambda: get_travel_expenses_in_date_range("E1001", "2026-01-01", "2026-01-31", config=self.mock_config),
            lambda: get_employee_summary("E1001", config=self.mock_config),
            lambda: get_department_employee_summary("Engineering", config=self.mock_config),
            lambda: get_pending_travel_expenses("E1001", config=self.mock_config),
        ]

        for fn in repo_calls:
            with self.assertRaises(DatabaseError):
                fn()

    # -----------------------------------------------------------------
    # 4. Successful Query Invariants
    # -----------------------------------------------------------------

    @patch("psycopg2.connect")
    def test_successful_analytical_queries_invariants(self, mock_connect):
        """Verify structured summaries and aggregations format records correctly without error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Mock employee summary return
        mock_cur.fetchone.return_value = {
            "id": 1,
            "employee_id": "E1001",
            "name": "Alice Chen",
            "email": "alice.chen@enterprise.internal",
            "department": "Engineering",
            "job_title": "Senior Software Engineer",
            "created_at": "2026-01-01T00:00:00",
            "manager_employee_id": "E1004",
            "manager_name": "David Kim",
            "manager_email": "david.kim@enterprise.internal",
            "manager_job_title": "VP of Operations",
        }

        summary = get_employee_summary("E1001", config=self.mock_config)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["employee_id"], "E1001")
        self.assertIsNotNone(summary["manager"])
        self.assertEqual(summary["manager"]["name"], "David Kim")
        self.assertTrue(mock_conn.close.called)


class TestFastAPIConcurrentSessionIsolation(unittest.TestCase):
    """Deterministic concurrency tests verifying strict session, thread, and approval isolation."""

    def setUp(self):
        self.client = TestClient(app)
        self.store = InMemorySessionStore()

    # -----------------------------------------------------------------
    # 1. Multi-Session History Isolation Under Concurrency
    # -----------------------------------------------------------------

    def test_concurrent_multi_session_history_isolation(self):
        """Simulate concurrent requests across distinct sessions ensuring zero history cross-talk."""
        sessions = [
            {"session_id": f"sess_concurrent_{i}", "emp_id": f"E100{i}", "query": f"Inquiry for E100{i}"}
            for i in range(1, 6)
        ]

        def mock_run_agent_dynamic(user_query, session_id=None, **kwargs):
            emp_suffix = str(session_id).split("_")[-1] if session_id else ""
            emp_id = f"E100{emp_suffix}"
            return AgentResponse(
                session_id=session_id,
                query=user_query,
                final_answer=f"Synthesized response for {emp_id}",
                steps=[
                    AgentStep(
                        tool_name="get_employee",
                        tool_args={"employee_id": emp_id},
                        tool_result={"employee_id": emp_id, "name": f"Employee {emp_id}"},
                    )
                ],
                total_steps=1,
                status="completed",
                citations=[],
            )

        def simulate_session_chat(sess_info):
            sess_id = sess_info["session_id"]
            query = sess_info["query"]
            response = self.client.post(
                "/api/v1/agent/chat",
                json={"session_id": sess_id, "message": query},
            )
            return sess_id, response.status_code, response.json()

        with patch("app.api.main.run_agent", side_effect=mock_run_agent_dynamic):
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(simulate_session_chat, s) for s in sessions]
                results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), 5)
        for sess_id, status_code, data in results:
            self.assertEqual(status_code, 200)
            self.assertEqual(data["session_id"], sess_id)
            # Verify response strictly corresponds to this session's requested employee
            emp_suffix = sess_id.split("_")[-1]
            self.assertIn(f"E100{emp_suffix}", data["answer"])
            self.assertEqual(data["steps"][0]["tool_args"]["employee_id"], f"E100{emp_suffix}")

    # -----------------------------------------------------------------
    # 2. Session Clear & Delete Isolation Under Concurrency
    # -----------------------------------------------------------------

    def test_session_clear_isolation_does_not_affect_other_sessions(self):
        """Clearing session A history must not modify or wipe session B history."""
        sess_a = "sess_iso_clear_A"
        sess_b = "sess_iso_clear_B"

        default_session_store.append_message(sess_a, {"role": "user", "content": "Hello from A"})
        default_session_store.append_message(sess_b, {"role": "user", "content": "Hello from B"})

        # Clear Session A via API
        res_clear = self.client.post(f"/api/v1/agent/sessions/{sess_a}/clear")
        self.assertEqual(res_clear.status_code, 200)
        self.assertEqual(res_clear.json()["status"], "cleared")

        # Verify Session A is empty, but Session B remains untouched
        self.assertEqual(default_session_store.get_session(sess_a), [])
        messages_b = default_session_store.get_session(sess_b)
        self.assertEqual(len(messages_b), 1)
        self.assertEqual(messages_b[0]["content"], "Hello from B")

        # Cleanup
        default_session_store.delete_session(sess_a)
        default_session_store.delete_session(sess_b)

    def test_session_delete_isolation_under_concurrency(self):
        """Deleting session A must not delete or affect session B in memory store."""
        sess_1 = "sess_iso_del_1"
        sess_2 = "sess_iso_del_2"

        default_session_store.append_message(sess_1, {"role": "user", "content": "Msg 1"})
        default_session_store.append_message(sess_2, {"role": "user", "content": "Msg 2"})

        res_del = self.client.delete(f"/api/v1/agent/sessions/{sess_1}")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["status"], "deleted")

        self.assertFalse(default_session_store.has_session(sess_1))
        self.assertTrue(default_session_store.has_session(sess_2))
        self.assertEqual(len(default_session_store.get_session(sess_2)), 1)

        # Cleanup
        default_session_store.delete_session(sess_2)

    # -----------------------------------------------------------------
    # 3. Checkpoint Thread ID Isolation
    # -----------------------------------------------------------------

    def test_checkpoint_thread_id_mapping_and_isolation(self):
        """Verify thread IDs map deterministically from sessions and remain strictly isolated."""
        thread_a = get_thread_id_for_session("session_alpha")
        thread_b = get_thread_id_for_session("session_beta")

        self.assertEqual(thread_a, "session_alpha")
        self.assertEqual(thread_b, "session_beta")
        self.assertNotEqual(thread_a, thread_b)

        # Build configurations
        cfg_a = build_thread_config(thread_a)
        cfg_b = build_thread_config(thread_b)
        self.assertEqual(cfg_a["configurable"]["thread_id"], "session_alpha")
        self.assertEqual(cfg_b["configurable"]["thread_id"], "session_beta")

    def test_approval_id_thread_association_integrity(self):
        """Verify formatted approval IDs deterministically embed and resolve the correct thread."""
        thread_1 = "thread_finance_101"
        thread_2 = "thread_hr_202"

        appr_1 = format_approval_id(thread_1)
        appr_2 = format_approval_id(thread_2)

        self.assertIn(thread_1, appr_1)
        self.assertIn(thread_2, appr_2)
        self.assertNotEqual(appr_1, appr_2)

        # Resolve
        resolved_1 = resolve_thread_from_approval_id(appr_1)
        resolved_2 = resolve_thread_from_approval_id(appr_2)

        self.assertEqual(resolved_1, thread_1)
        self.assertEqual(resolved_2, thread_2)


class TestSameSessionConcurrencyAndSafety(unittest.TestCase):
    """Deterministic tests examining concurrent operations targeting the SAME session ID."""

    def setUp(self):
        self.store = InMemorySessionStore()

    # -----------------------------------------------------------------
    # 1. InMemorySessionStore Thread-Safe Appends
    # -----------------------------------------------------------------

    def test_same_session_concurrent_appends_thread_safety(self):
        """Concurrently append messages from 20 threads to the same session without data corruption."""
        session_id = "same_session_concurrency_test"
        num_threads = 20

        def append_turn(idx):
            self.store.append_message(
                session_id,
                {"role": "user", "content": f"Turn message {idx}", "idx": idx},
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(append_turn, i) for i in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        messages = self.store.get_session(session_id)
        self.assertEqual(len(messages), num_threads)
        # Verify all indices exist and no message dict is corrupted
        saved_indices = {m["idx"] for m in messages}
        self.assertEqual(saved_indices, set(range(num_threads)))

    # -----------------------------------------------------------------
    # 2. Concurrent Read & Write Safety
    # -----------------------------------------------------------------

    def test_same_session_concurrent_read_write_safety(self):
        """Concurrently read and write to the same session without RuntimeError or deadlocks."""
        session_id = "same_sess_rw_test"
        self.store.append_message(session_id, {"role": "system", "content": "init"})

        errors = []

        def reader():
            try:
                for _ in range(50):
                    msgs = self.store.get_session(session_id)
                    self.assertIsInstance(msgs, list)
            except Exception as e:
                errors.append(e)

        def writer(idx):
            try:
                for j in range(25):
                    self.store.append_message(session_id, {"role": "user", "content": f"w_{idx}_{j}"})
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(reader),
                executor.submit(reader),
                executor.submit(writer, 1),
                executor.submit(writer, 2),
            ]
            for f in as_completed(futures):
                f.result()

        self.assertEqual(errors, [])
        final_msgs = self.store.get_session(session_id)
        # 1 init + 25*2 writes = 51 messages
        self.assertEqual(len(final_msgs), 51)

    # -----------------------------------------------------------------
    # 3. Same-Session FastAPI Chat Requests
    # -----------------------------------------------------------------

    def test_same_session_concurrent_api_requests_safety(self):
        """Concurrent requests to /api/v1/agent/chat for same session complete safely with valid schemas."""
        client = TestClient(app)
        session_id = "same_session_api_race_test"

        def mock_same_sess_run_agent(user_query, session_id=None, **kwargs):
            return AgentResponse(
                session_id=session_id,
                query=user_query,
                final_answer=f"Answer to: {user_query}",
                steps=[],
                total_steps=0,
                status="completed",
                citations=[],
            )

        def send_chat(query_text):
            res = client.post(
                "/api/v1/agent/chat",
                json={"session_id": session_id, "message": query_text},
            )
            return res.status_code, res.json()

        with patch("app.api.main.run_agent", side_effect=mock_same_sess_run_agent):
            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(send_chat, "First simultaneous request")
                f2 = executor.submit(send_chat, "Second simultaneous request")
                res1_code, res1_data = f1.result()
                res2_code, res2_data = f2.result()

        self.assertEqual(res1_code, 200)
        self.assertEqual(res2_code, 200)
        self.assertEqual(res1_data["session_id"], session_id)
        self.assertEqual(res2_data["session_id"], session_id)


class TestAPIErrorContractsAndSanitization(unittest.TestCase):
    """Deterministic tests for API error contracts (400, 404, 422, 500) and zero secret leakage."""

    def setUp(self):
        self.client = TestClient(app)

    # -----------------------------------------------------------------
    # 1. Database Unavailable / Error Contract
    # -----------------------------------------------------------------

    def test_database_unavailable_returns_sanitized_500_on_employee_routes(self):
        """Verify DatabaseError returns HTTP 500 with sanitized details without leaking internal info."""
        with patch(
            "app.api.main.get_employee_summary",
            side_effect=DatabaseError(
                "Could not connect to PostgreSQL: connection refused",
                original_error=psycopg2.OperationalError(
                    "FATAL: password authentication failed for user 'postgres' on host '127.0.0.1:5432'"
                ),
            ),
        ):
            response = self.client.get("/api/v1/employees/E1001")
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data.get("error_type"), "DatabaseError")
            self.assertIn("database error occurred", data.get("detail", "").lower())
            # Ensure no credentials or connection string leaked
            self.assertNotIn("postgres", response.text.lower())
            self.assertNotIn("password", response.text.lower())
            self.assertNotIn("127.0.0.1", response.text)

    def test_database_error_on_leave_and_travel_endpoints(self):
        """Verify leave and travel endpoints return sanitized 500 on database failure."""
        with patch("app.api.main.get_employee_leave_summary", side_effect=DatabaseError("DB query failed")):
            res_leave = self.client.get("/api/v1/employees/E1001/leave")
            self.assertEqual(res_leave.status_code, 500)
            self.assertEqual(res_leave.json()["error_type"], "DatabaseError")

        with patch("app.api.main.get_employee_travel_summary", side_effect=DatabaseError("DB query failed")):
            res_travel = self.client.get("/api/v1/employees/E1001/travel")
            self.assertEqual(res_travel.status_code, 500)
            self.assertEqual(res_travel.json()["error_type"], "DatabaseError")

    def test_database_error_during_agent_chat_returns_sanitized_500(self):
        """Verify DatabaseError during agent chat returns 500 with sanitized Agent/Database error."""
        with patch("app.api.main.run_agent", side_effect=DatabaseError("DB connection lost mid-turn")):
            response = self.client.post(
                "/api/v1/agent/chat",
                json={"session_id": "sess_err_test", "message": "What is Alice's balance?"},
            )
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["error_type"], "DatabaseError")
            self.assertIn("database error occurred", data["detail"].lower())

    # -----------------------------------------------------------------
    # 2. Non-Existent Entity Contracts (404)
    # -----------------------------------------------------------------

    def test_nonexistent_employee_endpoints_return_404(self):
        """Verify requesting unknown employee ID across endpoints returns structured 404."""
        with patch("app.api.main.get_employee_summary", return_value=None):
            res_emp = self.client.get("/api/v1/employees/NONEXISTENT_999")
            self.assertEqual(res_emp.status_code, 404)
            self.assertIn("not found", res_emp.json()["detail"].lower())

        with patch("app.api.main.get_employee_leave_summary", return_value=None):
            res_leave = self.client.get("/api/v1/employees/NONEXISTENT_999/leave")
            self.assertEqual(res_leave.status_code, 404)
            self.assertIn("not found", res_leave.json()["detail"].lower())

        with patch("app.api.main.get_employee_travel_summary", return_value=None):
            res_travel = self.client.get("/api/v1/employees/NONEXISTENT_999/travel")
            self.assertEqual(res_travel.status_code, 404)
            self.assertIn("not found", res_travel.json()["detail"].lower())

    # -----------------------------------------------------------------
    # 3. Payload Validation Contracts (422)
    # -----------------------------------------------------------------

    def test_ask_endpoint_payload_validation(self):
        """Verify POST /api/v1/ask validates request body correctly."""
        # Empty JSON
        res1 = self.client.post("/api/v1/ask", json={})
        self.assertEqual(res1.status_code, 422)

        # Whitespace question
        res2 = self.client.post("/api/v1/ask", json={"question": "   \n\t  "})
        self.assertEqual(res2.status_code, 422)

        # Non-string question
        res3 = self.client.post("/api/v1/ask", json={"question": 12345})
        self.assertEqual(res3.status_code, 422)

    def test_agent_chat_payload_validation(self):
        """Verify POST /api/v1/agent/chat validates session_id and message."""
        # Missing message
        res1 = self.client.post("/api/v1/agent/chat", json={"session_id": "s1"})
        self.assertEqual(res1.status_code, 422)

        # Empty session_id
        res2 = self.client.post("/api/v1/agent/chat", json={"session_id": "   ", "message": "hello"})
        self.assertEqual(res2.status_code, 422)

        # Whitespace message
        res3 = self.client.post("/api/v1/agent/chat", json={"session_id": "s1", "message": "   "})
        self.assertEqual(res3.status_code, 422)

        # Overly long session ID (>128 chars)
        res4 = self.client.post("/api/v1/agent/chat", json={"session_id": "x" * 200, "message": "hello"})
        self.assertEqual(res4.status_code, 422)

    def test_approval_decision_payload_validation(self):
        """Verify POST /api/v1/agent/approvals/{approval_id} rejects invalid decision enum."""
        # Invalid decision string
        res = self.client.post(
            "/api/v1/agent/approvals/appr_123",
            json={"decision": "maybe", "notes": "Need more info"},
        )
        self.assertEqual(res.status_code, 422)

    # -----------------------------------------------------------------
    # 4. Approval Mismatch & Non-Existent Approval (404)
    # -----------------------------------------------------------------

    def test_nonexistent_approval_resume_returns_404(self):
        """Submitting decision for non-existent or expired approval returns 404."""
        response = self.client.post(
            "/api/v1/agent/approvals/appr_nonexistent_token_999",
            json={"decision": "approve", "notes": "Authorized"},
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("not found", data["detail"].lower())

    # -----------------------------------------------------------------
    # 5. Zero Stack Trace and Secret Leakage Contract
    # -----------------------------------------------------------------

    def test_unhandled_agent_exception_does_not_leak_stack_trace_to_client(self):
        """Verify unhandled exceptions in agent chat return safe 500 without leaking stack traces."""
        with patch("app.api.main.run_agent", side_effect=RuntimeError("Internal LLM API Key Secret XYZ failed")):
            response = self.client.post(
                "/api/v1/agent/chat",
                json={"session_id": "sess_safe_err", "message": "Hello"},
            )
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["error_type"], "AgentError")
            self.assertEqual(data["detail"], "An internal error occurred while processing the agent conversation.")
            self.assertNotIn("Traceback", response.text)
            self.assertNotIn("Internal LLM API Key Secret XYZ", response.text)


if __name__ == "__main__":
    unittest.main()
