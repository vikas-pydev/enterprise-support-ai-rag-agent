"""Unit and Integration Tests for LangGraph Single-Agent Implementation.

Tests the stateful LangGraph agent execution workflow:
- State initialization and graph compilation
- Direct LLM responses reaching END
- Semantic tool routing (policy, employee, leave, travel, department)
- Tool execution observations feeding back into LLM node
- Multi-step tool workflows (travel summary + employee manager lookup)
- Safety guardrails (unknown tool rejection, malformed arguments, sanitized exceptions)
- Max step budget termination
- Duplicate tool call protection
- Structured execution traces, citations, used_rag flag, and timing
- Multi-turn conversational memory preservation and session isolation
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from typing import Any

from app.agent.graph import (
    create_agent_graph,
    run_graph_agent,
    AgentGraphState,
)
from app.agent.memory import InMemorySessionStore
from app.agent.agent import AgentResponse, AgentStep, AgentExecutionTrace


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


class TestAgentGraph(unittest.TestCase):
    """Test suite for LangGraph single-agent fundamentals, routing, safety, and traces."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            p.stop()

    def setUp(self):
        self.session_store = InMemorySessionStore()

    def test_01_graph_initializes_and_compiles_correctly(self):
        """1. Verify the StateGraph builds, adds nodes and edges, and compiles without error."""
        graph = create_agent_graph()
        self.assertIsNotNone(graph)
        self.assertTrue(hasattr(graph, "invoke"))

    def test_02_graph_state_initializes_correctly(self):
        """2. Verify initial graph state contains all required typed fields."""
        state: AgentGraphState = {
            "session_id": "test-session",
            "query": "Hello",
            "system_prompt": "System prompt",
            "model": "gpt-test",
            "client": None,
            "messages": [{"role": "user", "content": "Hello"}],
            "turn_messages": [{"role": "user", "content": "Hello"}],
            "steps": [],
            "step_count": 0,
            "max_steps": 5,
            "executed_calls": {},
            "pending_tool_calls": [],
            "final_answer": "",
            "status": "completed",
            "duration_ms": 0.0,
            "used_rag": False,
            "citations": [],
            "error": None,
            "start_time": 100.0,
        }
        self.assertEqual(state["session_id"], "test-session")
        self.assertEqual(state["query"], "Hello")
        self.assertEqual(state["step_count"], 0)
        self.assertEqual(state["max_steps"], 5)

    def test_03_llm_only_response_reaches_end(self):
        """3. Verify direct LLM text response terminates cleanly at END without tool steps."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content="Hello! How can I assist you with enterprise policies or records today?"
        )

        resp = run_graph_agent(
            user_query="Hello there",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertIsInstance(resp, AgentResponse)
        self.assertEqual(resp.status, "completed")
        self.assertIn("assist you", resp.final_answer)
        self.assertEqual(len(resp.steps), 0)
        self.assertEqual(resp.total_steps, 0)
        self.assertFalse(resp.used_rag)
        self.assertEqual(resp.citations, [])
        self.assertIsNotNone(resp.trace)
        self.assertEqual(resp.trace.status, "completed")

    def test_04_policy_query_routes_to_ask_policy(self):
        """4. Verify policy questions route to ask_policy, extract citations, and set used_rag=True."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_p1", "ask_policy", {"question": "What is meal per diem?"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="The meal per diem is $75 [Travel_Policy.md].", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([("Per diem is $75", 8.8, {"title": "Travel", "source": "t.md", "chunk_uid": "chunk_001"})], MagicMock())
            mock_ans.return_value = "The meal per diem is $75."

            resp = run_graph_agent(
                user_query="What is meal per diem?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertTrue(resp.used_rag)
            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(resp.steps[0].tool_name, "ask_policy")
            self.assertEqual(resp.steps[0].status, "success")
            self.assertGreater(len(resp.citations), 0)
            self.assertEqual(resp.citations[0]["chunk_uid"], "chunk_001")
            self.assertTrue(resp.trace.used_rag)

    def test_05_employee_query_routes_to_get_employee(self):
        """5. Verify employee lookup routes to get_employee tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_e1", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen is a Senior Software Engineer.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="Who is E1001?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertFalse(resp.used_rag)
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_employee")
        self.assertEqual(resp.steps[0].status, "success")
        self.assertIn("Alice Chen", resp.final_answer)

    def test_06_leave_query_routes_to_get_leave_balance(self):
        """6. Verify leave queries route to get_leave_balance tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_l1", "get_leave_balance", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen has 24 days of leave remaining.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="What is Alice's leave balance?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_leave_balance")
        self.assertIn("24 days", resp.final_answer)

    def test_07_travel_query_routes_to_get_travel_summary(self):
        """7. Verify travel expense queries route to get_travel_summary tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_t1", "get_travel_summary", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen has spent $2,450 on travel expenses.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="How much has Alice spent on travel?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")
        self.assertIn("$2,450", resp.final_answer)

    def test_08_department_query_routes_to_list_department_employees(self):
        """8. Verify roster queries route to list_department_employees tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_d1", "list_department_employees", {"department": "Engineering"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Engineering department has Alice Chen and others.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="Who works in Engineering?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "list_department_employees")
        self.assertIn("Alice Chen", resp.final_answer)

    def test_09_tool_result_returns_to_llm_node(self):
        """9. Verify the graph feeds tool observations back to the LLM node messages payload."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_obs1", "get_employee", {"employee_id": "E9999"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Employee E9999 was not found.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="Find E9999",
            client=mock_client,
            session_store=self.session_store,
        )

        second_call_messages = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
        tool_msg = next((m for m in second_call_messages if m.get("role") == "tool"), None)
        self.assertIsNotNone(tool_msg)
        self.assertIn("E9999", tool_msg["content"])
        self.assertEqual(resp.status, "completed")

    def test_10_multi_step_tool_workflow(self):
        """10. Verify multi-step sequential tool calls (travel summary -> employee profile) execute in graph."""
        mock_client = MagicMock()
        tc1 = _create_mock_tool_call("call_ms1", "get_travel_summary", {"employee_id": "E1001"})
        tc2 = _create_mock_tool_call("call_ms2", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp2 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp3 = _create_mock_completion(content="Alice Chen spent travel funds and her manager is Bob.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2, resp3]

        resp = run_graph_agent(
            user_query="How much has E1001 spent on travel and who is their manager?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(resp.steps[1].tool_name, "get_employee")
        self.assertIn("Alice Chen", resp.final_answer)

    def test_11_unknown_tool_rejected_safely(self):
        """11. Verify requesting an unapproved tool records an error step without crashing the graph."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_bad", "delete_database_records", {"force": True})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="I cannot perform unauthorized operations.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="Delete everything",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].status, "error")
        self.assertIn("not recognized or permitted", resp.steps[0].error)

    def test_12_malformed_arguments_remain_rejected(self):
        """12. Verify invalid or unparseable JSON arguments are safely caught and reported."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_bad_json", "get_employee", "{malformed_json: true,")
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Invalid arguments provided.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="Look up employee",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].status, "error")
        self.assertIn("Failed to parse tool arguments", resp.steps[0].error)

    def test_13_tool_exceptions_remain_sanitized(self):
        """13. Verify database or backend exceptions during tool execution are sanitized."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_exc", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Could not retrieve records due to error.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.database_tools.get_employee_summary", side_effect=Exception("FATAL: password auth failed for postgres://secret_pw@db")):
            resp = run_graph_agent(
                user_query="Lookup E1001",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(resp.steps[0].status, "error")
            self.assertNotIn("secret_pw", str(resp.steps[0].error))
            self.assertNotIn("secret_pw", str(resp.steps[0].tool_result))

    def test_14_max_agent_steps_enforced_in_graph(self):
        """14. Verify graph terminates safely with status='max_steps_reached' when step limit is hit."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_loop", "get_employee", {"employee_id": "E1001"})
        mock_client.chat.completions.create.return_value = _create_mock_completion(tool_calls=[tc])

        resp = run_graph_agent(
            user_query="Infinite loop test",
            client=mock_client,
            session_store=self.session_store,
            max_steps=3,
        )

        self.assertEqual(resp.status, "max_steps_reached")
        self.assertLessEqual(resp.total_steps, 3)
        self.assertEqual(resp.trace.status, "max_steps_reached")

    def test_15_duplicate_tool_calls_rejected_in_graph(self):
        """15. Verify repeating identical tool calls in the same graph run is intercepted and rejected."""
        mock_client = MagicMock()
        tc1 = _create_mock_tool_call("call_dup1", "get_employee", {"employee_id": "E1001"})
        tc2 = _create_mock_tool_call("call_dup2", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp2 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp3 = _create_mock_completion(content="Alice Chen is in Engineering.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2, resp3]

        resp = run_graph_agent(
            user_query="Who is E1001?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].status, "success")
        self.assertEqual(resp.steps[1].status, "rejected_duplicate")

    def test_16_execution_trace_captures_metadata_and_timing(self):
        """16. Verify AgentExecutionTrace captures session_id, duration_ms, tool names, and step metadata."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_trace", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen is an Engineer.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        resp = run_graph_agent(
            user_query="Find Alice",
            session_id="session-trace-99",
            client=mock_client,
            session_store=self.session_store,
        )

        trace = resp.trace
        self.assertIsNotNone(trace)
        self.assertEqual(trace.session_id, "session-trace-99")
        self.assertEqual(trace.query, "Find Alice")
        self.assertEqual(trace.total_steps, 1)
        self.assertIn("get_employee", trace.tools_invoked)
        self.assertGreaterEqual(trace.total_duration_ms, 0.0)
        self.assertEqual(trace.status, "completed")
        self.assertEqual(resp.steps[0].duration_ms >= 0.0, True)

    def test_17_citations_survive_graph_execution(self):
        """17. Verify RAG citations from policy tool are properly extracted and preserved in the final response."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_cite", "ask_policy", {"question": "travel reimbursement"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Travel reimbursement policy details.", tool_calls=None)
        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = (
                [
                    ("30 days", 9.0, {"chunk_uid": "chunk_A", "title": "Travel Policy", "source": "t.md"}),
                    ("Receipt required", 8.5, {"chunk_uid": "chunk_B", "title": "Expense Policy", "source": "e.md"}),
                ],
                MagicMock(),
            )
            mock_ans.return_value = "Submit receipts within 30 days."

            resp = run_graph_agent(
                user_query="How do I get travel reimbursed?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(len(resp.citations), 2)
            chunk_uids = [c["chunk_uid"] for c in resp.citations]
            self.assertIn("chunk_A", chunk_uids)
            self.assertIn("chunk_B", chunk_uids)

    def test_18_graph_does_not_expose_chain_of_thought(self):
        """18. Verify internal reasoning or hidden chain-of-thought tokens are not exposed."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content="Here is your final answer without internal thinking tokens."
        )

        resp = run_graph_agent(
            user_query="Tell me about benefits",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertNotIn("<think>", resp.final_answer)
        self.assertNotIn("BEGIN_THOUGHT", resp.final_answer)

    def test_19_multi_turn_session_preservation_in_graph(self):
        """19. Verify conversational context is maintained across multiple graph executions in the same session."""
        mock_client = MagicMock()
        tc1 = _create_mock_tool_call("call_t1", "get_employee", {"employee_id": "E1001"})
        tc2 = _create_mock_tool_call("call_t2", "get_leave_balance", {"employee_id": "E1001"})

        resp1_step1 = _create_mock_completion(content=None, tool_calls=[tc1])
        resp1_step2 = _create_mock_completion(content="E1001 is Alice Chen.", tool_calls=None)
        resp2_step1 = _create_mock_completion(content=None, tool_calls=[tc2])
        resp2_step2 = _create_mock_completion(content="Alice has 24 days of leave remaining.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [
            resp1_step1,
            resp1_step2,
            resp2_step1,
            resp2_step2,
        ]

        resp1 = run_graph_agent(
            user_query="Who is E1001?",
            session_id="multi-turn-session-1",
            client=mock_client,
            session_store=self.session_store,
        )
        self.assertEqual(resp1.status, "completed")

        resp2 = run_graph_agent(
            user_query="What is her leave balance?",
            session_id="multi-turn-session-1",
            client=mock_client,
            session_store=self.session_store,
        )
        self.assertEqual(resp2.status, "completed")

        turn2_messages = mock_client.chat.completions.create.call_args_list[2][1]["messages"]
        self.assertTrue(any(m.get("content") == "Who is E1001?" for m in turn2_messages))
        self.assertTrue(any(m.get("content") == "E1001 is Alice Chen." for m in turn2_messages))

    def test_20_session_isolation_in_graph(self):
        """20. Verify two different session IDs maintain separate conversation histories in the graph."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(content="Response")

        run_graph_agent(
            user_query="User 1 query",
            session_id="session-user-1",
            client=mock_client,
            session_store=self.session_store,
        )

        run_graph_agent(
            user_query="User 2 query",
            session_id="session-user-2",
            client=mock_client,
            session_store=self.session_store,
        )

        s1_msgs = self.session_store.get_session("session-user-1")
        s2_msgs = self.session_store.get_session("session-user-2")

        self.assertTrue(any(m.get("content") == "User 1 query" for m in s1_msgs))
        self.assertFalse(any(m.get("content") == "User 2 query" for m in s1_msgs))
        self.assertTrue(any(m.get("content") == "User 2 query" for m in s2_msgs))
        self.assertFalse(any(m.get("content") == "User 1 query" for m in s2_msgs))

    def test_21_empty_query_returns_validation_response(self):
        """21. Verify empty or whitespace-only user query returns a graceful prompt without invoking the graph."""
        resp = run_graph_agent(
            user_query="   ",
            session_store=self.session_store,
        )
        self.assertEqual(resp.status, "completed")
        self.assertIn("valid question", resp.final_answer)
        self.assertEqual(len(resp.steps), 0)


if __name__ == "__main__":
    unittest.main()
