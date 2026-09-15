"""Comprehensive Automated Tests for Multi-Turn Conversational Memory & FastAPI Agent API (Phase 6 Task 2).

Tests:
1. New session starts empty
2. First message creates/uses session
3. Second message sees previous context
4. Pronoun/follow-up query works with previous entity context
5. Session A isolation
6. Session B isolation
7. Session clearing
8. Independent new session
9. Multi-turn tool call flow
10. Existing single-turn agent behavior still works
11. API endpoint accepts valid request
12. API response schema validation
13. Empty message validation (422)
14. Invalid/missing session validation (422)
15. Agent error is sanitized
16. Database error is sanitized
17. Citations survive through agent API when RAG is used
18. MAX_AGENT_STEPS still enforced in multi-turn sessions
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.agent.agent import run_agent, AgentResponse, AgentStep, MAX_AGENT_STEPS
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


class TestConversationalMemoryAndAgentAPI(unittest.TestCase):
    """Test suite for conversational memory, session isolation, and FastAPI agent endpoint."""

    def setUp(self):
        """Set up fresh isolated session store and API client for each test."""
        self.store = InMemorySessionStore()
        self.client = TestClient(app)
        default_session_store.clear_session("test_session_global")

    # -----------------------------------------------------------------
    # 1. New session starts empty
    # -----------------------------------------------------------------
    def test_01_new_session_starts_empty(self):
        """1. Verify that a new uninitialized session returns an empty message history."""
        self.assertFalse(self.store.has_session("session_101"))
        messages = self.store.get_session("session_101")
        self.assertEqual(messages, [])

    # -----------------------------------------------------------------
    # 2. First message creates/uses session
    # -----------------------------------------------------------------
    def test_02_first_message_creates_session_history(self):
        """2. Verify that executing the first turn stores user and assistant messages."""
        mock_client = MagicMock()
        resp = _create_mock_completion(content="Hello! How can I assist you with enterprise support today?")
        mock_client.chat.completions.create.return_value = resp

        session_id = "session_turn1"
        res = run_agent("Hello", session_id=session_id, session_store=self.store, client=mock_client)

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.session_id, session_id)
        self.assertTrue(self.store.has_session(session_id))

        history = self.store.get_session(session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Hello! How can I assist you with enterprise support today?")

    # -----------------------------------------------------------------
    # 3. Second message sees previous context
    # -----------------------------------------------------------------
    def test_03_second_message_sees_previous_context(self):
        """3. Verify that turn 2 passes the previous turn's messages in LLM request payload."""
        mock_client = MagicMock()
        resp1 = _create_mock_completion(content="Alice Chen is an engineer (E1001).")
        resp2 = _create_mock_completion(content="Her manager is David Kim.")
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        session_id = "session_context_test"
        # Turn 1
        run_agent("Who is E1001?", session_id=session_id, session_store=self.store, client=mock_client)

        # Turn 2
        run_agent("Who is their manager?", session_id=session_id, session_store=self.store, client=mock_client)

        # Inspect messages sent to LLM in turn 2
        call_args_turn2 = mock_client.chat.completions.create.call_args_list[1]
        sent_messages = call_args_turn2[1]["messages"]

        roles = [m["role"] for m in sent_messages]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])
        self.assertEqual(sent_messages[1]["content"], "Who is E1001?")
        self.assertEqual(sent_messages[2]["content"], "Alice Chen is an engineer (E1001).")
        self.assertEqual(sent_messages[3]["content"], "Who is their manager?")

    # -----------------------------------------------------------------
    # 4. Pronoun/follow-up query works with previous entity context
    # -----------------------------------------------------------------
    def test_04_pronoun_resolution_with_previous_entity(self):
        """4. Verify follow-up pronoun query leverages prior turn context to execute tool."""
        mock_client = MagicMock()

        # Turn 1: Ask employee info
        tc1 = _create_mock_tool_call("call_emp", "get_employee", {"employee_id": "E1001"})
        resp1_step1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp1_step2 = _create_mock_completion(content="Alice Chen (E1001) is a Senior Software Engineer.")

        # Turn 2: Ask "What about their travel expenses?" -> LLM resolves "their" to E1001
        tc2 = _create_mock_tool_call("call_trav", "get_travel_summary", {"employee_id": "E1001"})
        resp2_step1 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp2_step2 = _create_mock_completion(content="Alice Chen has total travel expenses of $425.00.")

        mock_client.chat.completions.create.side_effect = [
            resp1_step1, resp1_step2,
            resp2_step1, resp2_step2,
        ]

        session_id = "session_pronoun_resolution"

        # Execute Turn 1
        res1 = run_agent("What is the employee information for E1001?", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(res1.status, "completed")
        self.assertEqual(res1.steps[0].tool_name, "get_employee")

        # Execute Turn 2
        res2 = run_agent("What about their travel expenses?", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(res2.status, "completed")
        self.assertEqual(res2.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(res2.steps[0].tool_args, {"employee_id": "E1001"})
        self.assertIn("$425.00", res2.final_answer)

    # -----------------------------------------------------------------
    # 5. Session A isolation
    # -----------------------------------------------------------------
    def test_05_session_a_isolation(self):
        """5. Verify that Session A conversation is not visible to Session B."""
        mock_client = MagicMock()
        resp_a = _create_mock_completion(content="Alice Chen info for Session A.")
        resp_b = _create_mock_completion(content="Bob Smith info for Session B.")
        mock_client.chat.completions.create.side_effect = [resp_a, resp_b]

        run_agent("Employee E1001", session_id="session_A", session_store=self.store, client=mock_client)
        run_agent("Employee E1002", session_id="session_B", session_store=self.store, client=mock_client)

        history_a = self.store.get_session("session_A")
        history_b = self.store.get_session("session_B")

        self.assertEqual(len(history_a), 2)
        self.assertEqual(len(history_b), 2)
        self.assertEqual(history_a[0]["content"], "Employee E1001")
        self.assertEqual(history_b[0]["content"], "Employee E1002")

        # Verify Session B payload never contained Session A content
        call_args_b = mock_client.chat.completions.create.call_args_list[1]
        sent_messages_b = call_args_b[1]["messages"]
        all_text_b = " ".join(m.get("content", "") for m in sent_messages_b)
        self.assertNotIn("E1001", all_text_b)
        self.assertIn("E1002", all_text_b)

    # -----------------------------------------------------------------
    # 6. Session B isolation
    # -----------------------------------------------------------------
    def test_06_session_b_isolation(self):
        """6. Verify concurrent / interleaved messages across sessions maintain strict separation."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            _create_mock_completion(content="Answer A1"),
            _create_mock_completion(content="Answer B1"),
            _create_mock_completion(content="Answer A2"),
            _create_mock_completion(content="Answer B2"),
        ]

        run_agent("Query A1", session_id="sess_A", session_store=self.store, client=mock_client)
        run_agent("Query B1", session_id="sess_B", session_store=self.store, client=mock_client)
        run_agent("Query A2", session_id="sess_A", session_store=self.store, client=mock_client)
        run_agent("Query B2", session_id="sess_B", session_store=self.store, client=mock_client)

        history_a = self.store.get_session("sess_A")
        history_b = self.store.get_session("sess_B")

        self.assertEqual(len(history_a), 4)
        self.assertEqual(len(history_b), 4)

        self.assertEqual(history_a[0]["content"], "Query A1")
        self.assertEqual(history_a[2]["content"], "Query A2")
        self.assertEqual(history_b[0]["content"], "Query B1")
        self.assertEqual(history_b[2]["content"], "Query B2")

    # -----------------------------------------------------------------
    # 7. Session clearing
    # -----------------------------------------------------------------
    def test_07_session_clearing(self):
        """7. Verify clearing a session removes message history and next turn starts clean."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            _create_mock_completion(content="Alice Chen E1001"),
            _create_mock_completion(content="Fresh start message"),
        ]

        session_id = "session_to_clear"
        run_agent("Who is E1001?", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(len(self.store.get_session(session_id)), 2)

        # Clear session
        cleared = self.store.clear_session(session_id)
        self.assertTrue(cleared)
        self.assertEqual(self.store.get_session(session_id), [])

        # Next turn starts fresh
        run_agent("Hello again", session_id=session_id, session_store=self.store, client=mock_client)
        sent_messages_turn2 = mock_client.chat.completions.create.call_args_list[1][1]["messages"]

        self.assertEqual(len(sent_messages_turn2), 2)  # system + new user message
        self.assertEqual(sent_messages_turn2[1]["content"], "Hello again")

    # -----------------------------------------------------------------
    # 8. Independent new session
    # -----------------------------------------------------------------
    def test_08_independent_new_session(self):
        """8. Verify creating a brand new session starts completely independent with no prior state."""
        self.store.append_message("old_session", {"role": "user", "content": "Old data"})
        new_session_id = "brand_new_session"

        self.assertFalse(self.store.has_session(new_session_id))
        self.assertEqual(self.store.get_session(new_session_id), [])

    # -----------------------------------------------------------------
    # 9. Multi-turn tool call flow
    # -----------------------------------------------------------------
    def test_09_multi_turn_tool_call_flow(self):
        """9. Verify multi-turn conversation where each turn uses different tools and preserves tool outputs in context."""
        mock_client = MagicMock()

        # Turn 1: get_employee
        tc1 = _create_mock_tool_call("call_1", "get_employee", {"employee_id": "E1001"})
        resp1_1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp1_2 = _create_mock_completion(content="Alice Chen is in Engineering.")

        # Turn 2: get_leave_balance (using context)
        tc2 = _create_mock_tool_call("call_2", "get_leave_balance", {"employee_id": "E1001"})
        resp2_1 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp2_2 = _create_mock_completion(content="She has 24 remaining leave days.")

        mock_client.chat.completions.create.side_effect = [resp1_1, resp1_2, resp2_1, resp2_2]

        session_id = "session_flow"
        res1 = run_agent("Look up E1001", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(res1.status, "completed")
        self.assertEqual(res1.steps[0].tool_name, "get_employee")

        res2 = run_agent("How many leave days does she have left?", session_id=session_id, session_store=self.store, client=mock_client)
        self.assertEqual(res2.status, "completed")
        self.assertEqual(res2.steps[0].tool_name, "get_leave_balance")
        self.assertIn("24 remaining", res2.final_answer)

        history = self.store.get_session(session_id)
        # Turn 1: user, assistant(tool_calls), tool(obs), assistant(final) -> 4 msgs
        # Turn 2: user, assistant(tool_calls), tool(obs), assistant(final) -> 4 msgs
        self.assertEqual(len(history), 8)

    # -----------------------------------------------------------------
    # 10. Existing single-turn agent behavior still works
    # -----------------------------------------------------------------
    def test_10_single_turn_agent_backward_compatibility(self):
        """10. Verify run_agent without session_id behaves exactly as single-turn without side-effects."""
        mock_client = MagicMock()
        resp = _create_mock_completion(content="Single turn response")
        mock_client.chat.completions.create.return_value = resp

        res = run_agent("Single turn query", session_id=None, client=mock_client)

        self.assertIsNone(res.session_id)
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.final_answer, "Single turn response")
        self.assertEqual(res.total_steps, 0)

    # -----------------------------------------------------------------
    # 11. API endpoint accepts valid request
    # -----------------------------------------------------------------
    def test_11_api_endpoint_accepts_valid_request(self):
        """11. Verify POST /api/v1/agent/chat processes valid request and returns 200."""
        mock_agent_response = AgentResponse(
            session_id="api_sess_1",
            query="Who is E1001?",
            final_answer="Alice Chen is an engineer.",
            steps=[AgentStep(tool_name="get_employee", tool_args={"employee_id": "E1001"}, tool_result={"found": True})],
            total_steps=1,
            status="completed",
            citations=[],
        )

        with patch("app.api.main.run_agent", return_value=mock_agent_response):
            payload = {"session_id": "api_sess_1", "message": "Who is E1001?"}
            response = self.client.post("/api/v1/agent/chat", json=payload)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["session_id"], "api_sess_1")
            self.assertEqual(data["query"], "Who is E1001?")
            self.assertEqual(data["answer"], "Alice Chen is an engineer.")
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["total_steps"], 1)

    # -----------------------------------------------------------------
    # 12. API response schema
    # -----------------------------------------------------------------
    def test_12_api_response_schema_validation(self):
        """12. Verify all expected fields and nested models are present in AgentChatResponse."""
        mock_agent_response = AgentResponse(
            session_id="api_schema_sess",
            query="Check policy",
            final_answer="The per diem is $75.",
            steps=[AgentStep(tool_name="ask_policy", tool_args={"question": "per diem"}, tool_result={"answer": "Per diem $75"})],
            total_steps=1,
            status="completed",
            citations=[{
                "rank": 1,
                "title": "Travel Policy",
                "source_file": "travel.md",
                "chunk_uid": "chunk_01",
                "rerank_score": 8.5,
                "snippet": "Per diem is $75 per day.",
            }],
        )

        with patch("app.api.main.run_agent", return_value=mock_agent_response):
            payload = {"session_id": "api_schema_sess", "message": "Check policy"}
            response = self.client.post("/api/v1/agent/chat", json=payload)

            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Top level fields
            for key in ["session_id", "query", "answer", "status", "steps", "total_steps", "citations"]:
                self.assertIn(key, data)

            # Steps structure
            self.assertEqual(len(data["steps"]), 1)
            self.assertIn("tool_name", data["steps"][0])
            self.assertIn("tool_args", data["steps"][0])
            self.assertIn("tool_result", data["steps"][0])

            # Citations structure
            self.assertEqual(len(data["citations"]), 1)
            citation = data["citations"][0]
            self.assertEqual(citation["rank"], 1)
            self.assertEqual(citation["title"], "Travel Policy")
            self.assertEqual(citation["source_file"], "travel.md")
            self.assertEqual(citation["chunk_uid"], "chunk_01")
            self.assertEqual(citation["rerank_score"], 8.5)
            self.assertEqual(citation["snippet"], "Per diem is $75 per day.")

    # -----------------------------------------------------------------
    # 13. Empty message validation
    # -----------------------------------------------------------------
    def test_13_empty_message_validation(self):
        """13. Verify POST /api/v1/agent/chat rejects empty or whitespace-only messages with 422."""
        # Empty message
        res1 = self.client.post("/api/v1/agent/chat", json={"session_id": "s1", "message": ""})
        self.assertEqual(res1.status_code, 422)

        # Whitespace-only message
        res2 = self.client.post("/api/v1/agent/chat", json={"session_id": "s1", "message": "   \n  "})
        self.assertEqual(res2.status_code, 422)

        # Missing message field
        res3 = self.client.post("/api/v1/agent/chat", json={"session_id": "s1"})
        self.assertEqual(res3.status_code, 422)

    # -----------------------------------------------------------------
    # 14. Invalid/missing session validation
    # -----------------------------------------------------------------
    def test_14_invalid_or_missing_session_validation(self):
        """14. Verify POST /api/v1/agent/chat rejects empty or whitespace-only session_id with 422."""
        # Empty session_id
        res1 = self.client.post("/api/v1/agent/chat", json={"session_id": "", "message": "Hello"})
        self.assertEqual(res1.status_code, 422)

        # Whitespace session_id
        res2 = self.client.post("/api/v1/agent/chat", json={"session_id": "    ", "message": "Hello"})
        self.assertEqual(res2.status_code, 422)

        # Missing session_id field
        res3 = self.client.post("/api/v1/agent/chat", json={"message": "Hello"})
        self.assertEqual(res3.status_code, 422)

    # -----------------------------------------------------------------
    # 15. Agent error is sanitized
    # -----------------------------------------------------------------
    def test_15_agent_error_is_sanitized(self):
        """15. Verify unexpected agent exceptions produce sanitized 500 without leaking secrets or traces."""
        with patch("app.api.main.run_agent", side_effect=RuntimeError("Internal LLM API Key Secret XYZ failed")):
            payload = {"session_id": "err_sess", "message": "Hello"}
            response = self.client.post("/api/v1/agent/chat", json=payload)

            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn("error_type", data)
            self.assertEqual(data["error_type"], "AgentError")
            self.assertNotIn("XYZ", response.text)
            self.assertNotIn("Traceback", response.text)

    # -----------------------------------------------------------------
    # 16. Database error is sanitized
    # -----------------------------------------------------------------
    def test_16_database_error_is_sanitized(self):
        """16. Verify database exception in agent execution produces sanitized 500 response."""
        with patch("app.api.main.run_agent", side_effect=DatabaseError("FATAL: password authentication failed for user 'postgres'")):
            payload = {"session_id": "db_err_sess", "message": "Who is E1001?"}
            response = self.client.post("/api/v1/agent/chat", json=payload)

            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertEqual(data["error_type"], "DatabaseError")
            self.assertNotIn("password", response.text.lower())
            self.assertNotIn("postgres", response.text.lower())

    # -----------------------------------------------------------------
    # 17. Citations survive through agent API when RAG is used
    # -----------------------------------------------------------------
    def test_17_citations_survive_through_agent_api(self):
        """17. Verify when ask_policy is invoked, citations flow through agent steps to final API response."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_rag", "ask_policy", {"question": "What is meal per diem?"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="The meal per diem allowance is $75.")

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.rag_tools.retrieve") as mock_retrieve, patch("app.tools.rag_tools.generate_answer") as mock_gen:
            mock_retrieve.return_value = (
                [("Per diem is $75 per day.", 9.2, {"title": "Travel Policy", "source": "travel.md", "chunk_uid": "chunk_travel_75"})],
                MagicMock(),
            )
            mock_gen.return_value = "The meal per diem allowance is $75."

            # Test run_agent citation extraction
            agent_res = run_agent("What is meal per diem?", session_id="rag_sess", session_store=self.store, client=mock_client)
            self.assertEqual(len(agent_res.citations), 1)
            self.assertEqual(agent_res.citations[0]["chunk_uid"], "chunk_travel_75")
            self.assertEqual(agent_res.citations[0]["title"], "Travel Policy")

    # -----------------------------------------------------------------
    # 18. MAX_AGENT_STEPS still enforced
    # -----------------------------------------------------------------
    def test_18_max_agent_steps_enforced_in_multi_turn(self):
        """18. Verify multi-turn session enforces max_steps iteration limit and synthesizes answer."""
        mock_client = MagicMock()
        # Create an infinite tool-calling loop
        tc = _create_mock_tool_call("loop_call", "get_employee", {"employee_id": "E1001"})
        loop_resp = _create_mock_completion(content=None, tool_calls=[tc])
        synthesis_resp = _create_mock_completion(content="Maximum step limit synthesis.", tool_calls=None)

        # 3 loop iterations + 1 synthesis call
        mock_client.chat.completions.create.side_effect = [loop_resp, loop_resp, loop_resp, synthesis_resp]

        session_id = "session_max_steps"
        res = run_agent("Infinite loop test", session_id=session_id, session_store=self.store, max_steps=3, client=mock_client)

        self.assertEqual(res.status, "max_steps_reached")
        self.assertEqual(res.total_steps, 3)
        self.assertEqual(res.final_answer, "Maximum step limit synthesis.")
        self.assertTrue(self.store.has_session(session_id))


class TestSessionLifecycleEndpoints(unittest.TestCase):
    """Test suite for session clear and delete endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        default_session_store.append_message("test_sess_clear", {"role": "user", "content": "Hello"})

    def test_clear_session_endpoint(self):
        """Verify POST /api/v1/agent/sessions/{session_id}/clear resets session history."""
        self.assertTrue(len(default_session_store.get_session("test_sess_clear")) > 0)

        response = self.client.post("/api/v1/agent/sessions/test_sess_clear/clear")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "test_sess_clear")
        self.assertEqual(data["status"], "cleared")
        self.assertEqual(default_session_store.get_session("test_sess_clear"), [])

    def test_delete_session_endpoint(self):
        """Verify DELETE /api/v1/agent/sessions/{session_id} completely removes session."""
        default_session_store.append_message("test_sess_del", {"role": "user", "content": "Hello"})
        self.assertTrue(default_session_store.has_session("test_sess_del"))

        response = self.client.delete("/api/v1/agent/sessions/test_sess_del")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "test_sess_del")
        self.assertEqual(data["status"], "deleted")
        self.assertFalse(default_session_store.has_session("test_sess_del"))


if __name__ == "__main__":
    unittest.main()
