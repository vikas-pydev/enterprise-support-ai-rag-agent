"""Comprehensive Automated Tests for Agent Reliability, Tool Routing & Observability (Phase 6 Task 3).

Test Categories:
A. Observability
   1. Execution trace created and populated
   2. Tool execution timing captured (duration_ms)
   3. Step metadata captured (step_number, status, args, duration, error)
   4. Final run status and used_rag flag captured

B. Routing Reliability
   5. Policy question routes to ask_policy
   6. Employee profile inquiry routes to get_employee
   7. Leave balance inquiry routes to get_leave_balance
   8. Travel summary inquiry routes to get_travel_summary
   9. Department roster inquiry routes to list_department_employees

C. Reliability & Fault Tolerance
   10. Unknown tool name safely rejected
   11. Malformed JSON arguments handled gracefully
   12. Missing required tool arguments handled gracefully
   13. Wrong argument types handled gracefully
   14. Tool execution exceptions handled safely
   15. Duplicate tool call protection prevents redundant executions
   16. MAX_AGENT_STEPS limit enforced with synthesis
   17. No-tool direct final answer works

D. Security & Sanitization
   18. Database errors sanitized without leaking credentials
   19. LLM / network exceptions sanitized
   20. No secrets or credentials leaked in response / logs
   21. Arbitrary SQL / execution keywords blocked

E. Multi-Turn Session Observability
   22. Execution trace works across multi-turn sessions
   23. Prior conversation context remains accessible across turns
   24. Strict session isolation between distinct sessions
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.agent.agent import (
    run_agent,
    AgentResponse,
    AgentStep,
    AgentExecutionTrace,
    TOOLS_BY_NAME,
    OPENAI_TOOL_SCHEMAS,
    MAX_AGENT_STEPS,
)
from app.agent.memory import InMemorySessionStore, default_session_store
from app.api.main import app
from app.database.exceptions import DatabaseError


def _create_mock_completion(content=None, tool_calls=None):
    """Helper to construct mock OpenAI ChatCompletion objects."""
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        role="assistant",
    )
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _create_mock_tool_call(call_id: str, name: str, arguments: dict | str):
    """Helper to construct mock ToolCall objects."""
    if isinstance(arguments, dict):
        args_str = json.dumps(arguments)
    else:
        args_str = str(arguments)

    fn = SimpleNamespace(name=name, arguments=args_str)
    return SimpleNamespace(id=call_id, function=fn, type="function")


from tests.mock_db_helper import setup_mock_db_if_offline


class TestAgentReliabilityAndObservability(unittest.TestCase):
    """Test suite verifying agent observability, routing accuracy, safety boundaries, and error handling."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            p.stop()

    def setUp(self):
        self.store = InMemorySessionStore()
        self.client = TestClient(app)

    # =================================================================
    # A. OBSERVABILITY TESTS
    # =================================================================

    def test_01_execution_trace_created(self):
        """1. Verify structured AgentExecutionTrace is created and populated on every run."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_trace_1", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen is a Senior Software Engineer.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Who is E1001?", session_id="sess_trace_01", session_store=self.store, client=mock_client)

        self.assertIsNotNone(res.trace)
        self.assertIsInstance(res.trace, AgentExecutionTrace)
        self.assertEqual(res.trace.session_id, "sess_trace_01")
        self.assertEqual(res.trace.query, "Who is E1001?")
        self.assertEqual(res.trace.total_steps, 1)
        self.assertEqual(res.trace.status, "completed")
        self.assertEqual(res.trace.tools_invoked, ["get_employee"])
        self.assertFalse(res.trace.used_rag)
        self.assertGreaterEqual(res.trace.total_duration_ms, 0.0)

    def test_02_tool_timing_captured(self):
        """2. Verify individual tool execution duration is measured and recorded in milliseconds."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_timing_1", "get_leave_balance", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen has 24 remaining days.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Check leave for E1001", client=mock_client)

        self.assertEqual(len(res.steps), 1)
        step = res.steps[0]
        self.assertGreaterEqual(step.duration_ms, 0.0)
        self.assertGreaterEqual(res.duration_ms, step.duration_ms)

    def test_03_step_metadata_captured(self):
        """3. Verify AgentStep captures step_number, tool_name, tool_args, status, duration, error."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_meta_1", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen is an engineer.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Profile E1001", client=mock_client)

        step = res.steps[0]
        self.assertEqual(step.step_number, 1)
        self.assertEqual(step.tool_name, "get_employee")
        self.assertEqual(step.tool_args, {"employee_id": "E1001"})
        self.assertEqual(step.status, "success")
        self.assertIsNone(step.error)
        self.assertIn("data", step.tool_result)

    def test_04_final_status_and_used_rag_captured(self):
        """4. Verify status and used_rag flags accurately reflect execution path."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_rag_1", "ask_policy", {"question": "What is meal per diem?"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="The meal per diem is $75.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([("Per diem is $75", 8.8, {"title": "Travel", "source": "t.md", "chunk_uid": "c1"})], MagicMock())
            mock_ans.return_value = "The meal per diem is $75."

            res = run_agent("What is the meal per diem?", client=mock_client)

            self.assertEqual(res.status, "completed")
            self.assertTrue(res.used_rag)
            self.assertTrue(res.trace.used_rag)
            self.assertEqual(len(res.citations), 1)

    # =================================================================
    # B. ROUTING RELIABILITY TESTS
    # =================================================================

    def test_05_policy_question_routes_to_ask_policy(self):
        """5. Verify general policy questions route to ask_policy."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_p", "ask_policy", {"question": "What is the pet insurance policy?"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Pet insurance is not covered under standard policy.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([], MagicMock())
            mock_ans.return_value = "Information not available."

            res = run_agent("What is the pet insurance policy?", client=mock_client)
            self.assertEqual(res.steps[0].tool_name, "ask_policy")

    def test_06_employee_question_routes_to_get_employee(self):
        """6. Verify employee profile questions route to get_employee."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_e", "get_employee", {"employee_id": "E1002"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Bob Smith is in Human Resources.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Who is employee E1002?", client=mock_client)
        self.assertEqual(res.steps[0].tool_name, "get_employee")
        self.assertEqual(res.steps[0].tool_args, {"employee_id": "E1002"})

    def test_07_leave_question_routes_to_get_leave_balance(self):
        """7. Verify PTO balance questions route to get_leave_balance."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_l", "get_leave_balance", {"employee_id": "E1002"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Bob Smith has 15 days remaining.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("How many PTO days does E1002 have?", client=mock_client)
        self.assertEqual(res.steps[0].tool_name, "get_leave_balance")
        self.assertEqual(res.steps[0].tool_args, {"employee_id": "E1002"})

    def test_08_travel_question_routes_to_get_travel_summary(self):
        """8. Verify expense claim questions route to get_travel_summary."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_t", "get_travel_summary", {"employee_id": "E1002"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Bob Smith has no travel expenses.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("What are E1002's travel expenses?", client=mock_client)
        self.assertEqual(res.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(res.steps[0].tool_args, {"employee_id": "E1002"})

    def test_09_department_question_routes_to_list_department_employees(self):
        """9. Verify department roster inquiries route to list_department_employees."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_d", "list_department_employees", {"department": "Human Resources"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Human Resources has 1 employee: Bob Smith.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Who is in the Human Resources department?", client=mock_client)
        self.assertEqual(res.steps[0].tool_name, "list_department_employees")
        self.assertEqual(res.steps[0].tool_args, {"department": "Human Resources"})

    # =================================================================
    # C. RELIABILITY & FAULT TOLERANCE TESTS
    # =================================================================

    def test_10_unknown_tool_rejected(self):
        """10. Verify unapproved / unknown tool requests fail safely with status='error'."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_bad", "drop_tables", {"confirm": True})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="I cannot perform unauthorized operations.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Drop all tables", client=mock_client)
        self.assertEqual(res.steps[0].status, "error")
        self.assertIn("not recognized or permitted", res.steps[0].error)

    def test_11_malformed_json_arguments_handled(self):
        """11. Verify malformed non-JSON tool argument strings fail safely."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_bad_json", "get_employee", "{malformed_json: true,")
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Invalid arguments provided.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Look up employee", client=mock_client)
        self.assertEqual(res.steps[0].status, "error")
        self.assertIn("Failed to parse tool arguments", res.steps[0].error)

    def test_12_missing_required_arguments_handled(self):
        """12. Verify missing required Pydantic fields fail safely."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_missing", "get_employee", {})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Missing employee_id.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Look up employee", client=mock_client)
        self.assertEqual(res.steps[0].status, "error")
        self.assertIn("Invalid tool arguments", res.steps[0].error)

    def test_13_wrong_argument_types_handled(self):
        """13. Verify unexpected argument payload types do not crash the agent."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_wrong_type", "list_department_employees", {"department": 12345})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Department not found.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Check department 12345", client=mock_client)
        self.assertIn(res.steps[0].status, ["success", "error"])

    def test_14_tool_execution_exception_handled(self):
        """14. Verify unexpected tool execution exceptions fail safely with status='error'."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_exc", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Could not retrieve records due to error.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.database_tools.get_employee_summary", side_effect=RuntimeError("Disk I/O failure")):
            res = run_agent("Look up E1001", client=mock_client)
            self.assertEqual(res.steps[0].status, "error")

    def test_15_duplicate_tool_call_handled(self):
        """15. Verify duplicate tool call with identical arguments in same run is rejected safely."""
        mock_client = MagicMock()
        # LLM calls get_employee(E1001) twice in the same turn
        tc1 = _create_mock_tool_call("call_dup_1", "get_employee", {"employee_id": "E1001"})
        tc2 = _create_mock_tool_call("call_dup_2", "get_employee", {"employee_id": "E1001"})

        resp1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp2 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp3 = _create_mock_completion(content="Alice Chen is an engineer (E1001).", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2, resp3]

        res = run_agent("Tell me about E1001", client=mock_client)

        self.assertEqual(len(res.steps), 2)
        self.assertEqual(res.steps[0].status, "success")
        self.assertEqual(res.steps[1].status, "rejected_duplicate")
        self.assertEqual(res.steps[1].error, "Duplicate tool call rejected.")
        self.assertEqual(res.status, "completed")

    def test_16_max_agent_steps_enforced(self):
        """16. Verify MAX_AGENT_STEPS is strictly enforced and synthesizes final answer."""
        mock_client = MagicMock()
        # Model loops continuously
        tc = _create_mock_tool_call("loop_call", "get_employee", {"employee_id": "E1001"})
        resp_loop = _create_mock_completion(content=None, tool_calls=[tc])
        resp_synth = _create_mock_completion(content="Reached max iterations summary.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp_loop, resp_loop, resp_synth]

        res = run_agent("Loop test", max_steps=2, client=mock_client)
        self.assertEqual(res.status, "max_steps_reached")
        self.assertEqual(res.total_steps, 2)
        self.assertEqual(res.final_answer, "Reached max iterations summary.")

    def test_17_no_tool_final_answer_works(self):
        """17. Verify conversational questions without tool calls complete with 0 steps."""
        mock_client = MagicMock()
        resp = _create_mock_completion(content="Good morning! How can I assist you?", tool_calls=None)
        mock_client.chat.completions.create.return_value = resp

        res = run_agent("Good morning", client=mock_client)
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 0)
        self.assertEqual(res.final_answer, "Good morning! How can I assist you?")
        self.assertFalse(res.used_rag)

    # =================================================================
    # D. SECURITY & SANITIZATION TESTS
    # =================================================================

    def test_18_database_error_sanitized(self):
        """18. Verify database exceptions return sanitized error without exposing credentials."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_dberr", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Database is unavailable.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.database_tools.get_employee_summary", side_effect=DatabaseError("FATAL: password auth failed")):
            res = run_agent("Look up E1001", client=mock_client)
            self.assertEqual(res.status, "completed")
            step_result_str = json.dumps(res.steps[0].tool_result)
            self.assertNotIn("password", step_result_str.lower())

    def test_19_llm_error_sanitized(self):
        """19. Verify LLM service exceptions return sanitized status='error' response."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("OpenAI API key sk-secret-12345 expired")

        res = run_agent("Hello", client=mock_client)
        self.assertEqual(res.status, "error")
        self.assertIn("error occurred while contacting", res.final_answer)
        self.assertNotIn("sk-secret-12345", res.final_answer)

    def test_20_no_secret_leakage_in_api_response(self):
        """20. Verify API responses never contain secret keys, connection strings, or raw traces."""
        mock_agent_response = AgentResponse(
            session_id="sec_sess",
            query="Test query",
            final_answer="Standard sanitized answer.",
            steps=[AgentStep(
                step_number=1,
                tool_name="get_employee",
                tool_args={"employee_id": "E1001"},
                tool_result={"found": True, "data": {"name": "Alice Chen"}},
                status="success",
                duration_ms=12.5,
                error=None,
            )],
            total_steps=1,
            duration_ms=45.2,
            status="completed",
            used_rag=False,
            citations=[],
            trace=AgentExecutionTrace(
                session_id="sec_sess",
                query="Test query",
                total_steps=1,
                total_duration_ms=45.2,
                used_rag=False,
                status="completed",
                tools_invoked=["get_employee"],
                steps=[],
            ),
        )

        with patch("app.api.main.run_agent", return_value=mock_agent_response):
            response = self.client.post("/api/v1/agent/chat", json={"session_id": "sec_sess", "message": "Test query"})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertNotIn("password", response.text.lower())
            self.assertNotIn("secret", response.text.lower())
            self.assertIn("duration_ms", data)
            self.assertIn("used_rag", data)
            self.assertIn("trace", data)

    def test_21_raw_sql_execution_impossible(self):
        """21. Verify no arbitrary SQL execution tools exist in registry."""
        for tool_name in TOOLS_BY_NAME:
            self.assertNotIn("sql", tool_name.lower())
            self.assertNotIn("exec", tool_name.lower())
            self.assertNotIn("raw", tool_name.lower())

    # =================================================================
    # E. MULTI-TURN SESSION OBSERVABILITY TESTS
    # =================================================================

    def test_22_execution_trace_works_across_session(self):
        """22. Verify execution traces are cleanly generated for each turn in a multi-turn session."""
        mock_client = MagicMock()
        # Turn 1: get_employee
        tc1 = _create_mock_tool_call("t1_call", "get_employee", {"employee_id": "E1001"})
        resp1_1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp1_2 = _create_mock_completion(content="Alice Chen is a Senior Software Engineer.")

        # Turn 2: get_leave_balance
        tc2 = _create_mock_tool_call("t2_call", "get_leave_balance", {"employee_id": "E1001"})
        resp2_1 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp2_2 = _create_mock_completion(content="She has 24 remaining leave days.")

        mock_client.chat.completions.create.side_effect = [resp1_1, resp1_2, resp2_1, resp2_2]

        session_id = "sess_trace_multiturn"
        res1 = run_agent("Who is E1001?", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(res1.trace.session_id, session_id)
        self.assertEqual(res1.trace.tools_invoked, ["get_employee"])
        self.assertEqual(res1.trace.total_steps, 1)

        res2 = run_agent("How much leave does she have?", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(res2.trace.session_id, session_id)
        self.assertEqual(res2.trace.tools_invoked, ["get_leave_balance"])
        self.assertEqual(res2.trace.total_steps, 1)

    def test_23_previous_context_remains_available(self):
        """23. Verify second turn message payload includes full preceding turn context."""
        mock_client = MagicMock()
        resp1 = _create_mock_completion(content="Alice Chen is an engineer.")
        resp2 = _create_mock_completion(content="Her manager is David Kim.")
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        session_id = "sess_ctx_check"
        run_agent("Who is E1001?", session_id=session_id, session_store=self.store, client=mock_client)
        run_agent("Who is their manager?", session_id=session_id, session_store=self.store, client=mock_client)

        turn2_messages = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
        self.assertEqual(len(turn2_messages), 4)  # system + user1 + assistant1 + user2

    def test_24_session_isolation_intact(self):
        """24. Verify complete session isolation between concurrent user sessions."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            _create_mock_completion(content="Alice in Sess A"),
            _create_mock_completion(content="Bob in Sess B"),
        ]

        run_agent("Query A", session_id="user_A", session_store=self.store, client=mock_client)
        run_agent("Query B", session_id="user_B", session_store=self.store, client=mock_client)

        hist_a = self.store.get_session("user_A")
        hist_b = self.store.get_session("user_B")

        self.assertEqual(len(hist_a), 2)
        self.assertEqual(len(hist_b), 2)
        self.assertEqual(hist_a[0]["content"], "Query A")
        self.assertEqual(hist_b[0]["content"], "Query B")


if __name__ == "__main__":
    unittest.main()
