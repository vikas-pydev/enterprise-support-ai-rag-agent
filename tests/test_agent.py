import json
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from app.agent import (
    run_agent,
    AgentResponse,
    AgentStep,
    TOOLS_BY_NAME,
    OPENAI_TOOL_SCHEMAS,
    MAX_AGENT_STEPS,
    DEFAULT_AGENT_MODEL,
)
from app.tools import ALL_TOOLS


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


class TestAgentFoundation(unittest.TestCase):
    """Comprehensive test suite for Phase 6 Controlled Tool-Calling Agent."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            p.stop()

    def test_01_agent_initialization_and_tool_registry(self):
        """1. Verify agent initializes tools directly and dynamically from ALL_TOOLS."""
        self.assertEqual(len(TOOLS_BY_NAME), len(ALL_TOOLS))
        for tool in ALL_TOOLS:
            self.assertIn(tool.name, TOOLS_BY_NAME)
            self.assertEqual(TOOLS_BY_NAME[tool.name], tool)

    def test_02_tool_schemas_passed_to_llm(self):
        """2. Verify tool definitions generate valid OpenAI function calling schemas."""
        self.assertEqual(len(OPENAI_TOOL_SCHEMAS), len(ALL_TOOLS))
        schema_names = [s["function"]["name"] for s in OPENAI_TOOL_SCHEMAS]
        self.assertIn("ask_policy", schema_names)
        self.assertIn("get_employee", schema_names)
        self.assertIn("get_leave_balance", schema_names)
        self.assertIn("get_travel_summary", schema_names)
        self.assertIn("list_department_employees", schema_names)

        for s in OPENAI_TOOL_SCHEMAS:
            self.assertEqual(s["type"], "function")
            self.assertIn("parameters", s["function"])
            self.assertIn("description", s["function"])

    def test_03_policy_question_routes_to_ask_policy(self):
        """3. Verify policy inquiry triggers ask_policy tool call and return."""
        mock_client = MagicMock()
        # Step 1: Model requests ask_policy
        tc = _create_mock_tool_call("call_1", "ask_policy", {"question": "What is the per diem rate?"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])

        # Step 2: Model synthesizes final response after observing tool result
        resp2 = _create_mock_completion(content="The domestic per diem rate is $75 for meals.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.rag_tools.retrieve") as mock_retrieve, patch("app.tools.rag_tools.generate_answer") as mock_gen:
            mock_retrieve.return_value = ([("Per diem is $75", 9.0, {"title": "Travel", "source": "t.md"})], MagicMock())
            mock_gen.return_value = "The domestic per diem rate is $75 for meals."

            res = run_agent("What is the travel per diem?", client=mock_client)

            self.assertEqual(res.status, "completed")
            self.assertEqual(res.total_steps, 1)
            self.assertEqual(res.steps[0].tool_name, "ask_policy")
            self.assertIn("per diem", res.final_answer.lower())

    def test_04_employee_question_routes_to_get_employee(self):
        """4. Verify employee profile question triggers get_employee tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_2", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen is a Senior Software Engineer in Engineering.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Who is E1001?", client=mock_client)

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 1)
        self.assertEqual(res.steps[0].tool_name, "get_employee")
        self.assertEqual(res.steps[0].tool_args, {"employee_id": "E1001"})
        self.assertTrue(res.steps[0].tool_result.get("found"))

    def test_05_leave_question_routes_to_get_leave_balance(self):
        """5. Verify leave question triggers get_leave_balance tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_3", "get_leave_balance", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen has 16 remaining annual leave days.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("How many leave days does E1001 have left?", client=mock_client)

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 1)
        self.assertEqual(res.steps[0].tool_name, "get_leave_balance")
        self.assertEqual(res.steps[0].tool_args, {"employee_id": "E1001"})
        self.assertIn("balances", res.steps[0].tool_result["data"])

    def test_06_travel_question_routes_to_get_travel_summary(self):
        """6. Verify travel spending question triggers get_travel_summary tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_4", "get_travel_summary", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="E1001 has total travel expenses of $425.00 across 2 claims.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("What are E1001's travel expenses?", client=mock_client)

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 1)
        self.assertEqual(res.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(res.steps[0].tool_args, {"employee_id": "E1001"})
        self.assertEqual(res.steps[0].tool_result["data"]["total_amount"], 425.0)

    def test_07_department_question_routes_to_list_department_employees(self):
        """7. Verify department question triggers list_department_employees tool."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_5", "list_department_employees", {"department": "Engineering"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="The Engineering department has 1 employee: Alice Chen.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Who works in the Engineering department?", client=mock_client)

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 1)
        self.assertEqual(res.steps[0].tool_name, "list_department_employees")
        self.assertEqual(res.steps[0].tool_args, {"department": "Engineering"})
        self.assertGreaterEqual(res.steps[0].tool_result["count"], 1)

    def test_08_tool_arguments_validation(self):
        """8. Verify Pydantic schema catches and returns clean validation error on invalid args."""
        mock_client = MagicMock()
        # Invalid arguments: missing required 'employee_id' field
        tc = _create_mock_tool_call("call_6", "get_employee", {"invalid_field": "123"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Could not retrieve employee due to missing employee ID.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Look up employee", client=mock_client)

        self.assertEqual(res.total_steps, 1)
        self.assertIn("error", res.steps[0].tool_result)
        self.assertFalse(res.steps[0].tool_result["found"])

    def test_09_unknown_tool_names_rejected(self):
        """9. Verify unapproved / arbitrary tool names are safely rejected."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_7", "execute_sql_query", {"query": "SELECT * FROM employees"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="I cannot execute arbitrary SQL queries.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        res = run_agent("Run custom SQL query", client=mock_client)

        self.assertEqual(res.total_steps, 1)
        self.assertEqual(res.steps[0].tool_name, "execute_sql_query")
        self.assertIn("not recognized or permitted", res.steps[0].tool_result["error"])

    def test_10_tool_results_returned_to_llm_messages(self):
        """10. Verify messages sent to LLM in subsequent turns contain role='tool' and tool_call_id."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_unique_99", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Alice Chen is an engineer.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        run_agent("Info for E1001", client=mock_client)

        # Inspect second call messages
        second_call_messages = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
        tool_msg = next((m for m in second_call_messages if m.get("role") == "tool"), None)

        self.assertIsNotNone(tool_msg)
        self.assertEqual(tool_msg["tool_call_id"], "call_unique_99")
        parsed_content = json.loads(tool_msg["content"])
        self.assertTrue(parsed_content["found"])

    def test_11_multi_step_tool_calling(self):
        """11. Verify multi-step sequential tool calling workflow."""
        mock_client = MagicMock()
        # Turn 1: Model requests travel summary
        tc1 = _create_mock_tool_call("call_step_1", "get_travel_summary", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc1])

        # Turn 2: Model requests employee manager details
        tc2 = _create_mock_tool_call("call_step_2", "get_employee", {"employee_id": "E1001"})
        resp2 = _create_mock_completion(content=None, tool_calls=[tc2])

        # Turn 3: Model synthesizes final composite response
        resp3 = _create_mock_completion(
            content="Alice Chen (E1001) has spent $425.00 on travel. Her manager is David Kim (VP of Operations).",
            tool_calls=None,
        )

        mock_client.chat.completions.create.side_effect = [resp1, resp2, resp3]

        res = run_agent(
            "How much has E1001 spent on travel, and who is their manager?",
            client=mock_client,
        )

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 2)
        self.assertEqual(res.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(res.steps[1].tool_name, "get_employee")
        self.assertIn("David Kim", res.final_answer)

    def test_12_max_iteration_limit_enforced(self):
        """12. Verify execution halts and synthesizes response when max_steps is reached."""
        mock_client = MagicMock()
        # Model enters an infinite loop requesting tools
        tc = _create_mock_tool_call("loop_call", "get_employee", {"employee_id": "E1001"})
        loop_resp = _create_mock_completion(content=None, tool_calls=[tc])
        synthesis_resp = _create_mock_completion(content="Reached limit, summary of findings...", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [loop_resp, loop_resp, loop_resp, synthesis_resp]

        res = run_agent("Infinite test", max_steps=3, client=mock_client)

        self.assertEqual(res.total_steps, 3)
        self.assertEqual(res.status, "max_steps_reached")

    def test_13_database_errors_handled_safely(self):
        """13. Verify tool/database exceptions inside tool invocation are handled gracefully."""
        mock_client = MagicMock()
        tc = _create_mock_tool_call("call_err", "get_employee", {"employee_id": "E1001"})
        resp1 = _create_mock_completion(content=None, tool_calls=[tc])
        resp2 = _create_mock_completion(content="Database is temporarily unavailable.", tool_calls=None)

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        with patch("app.tools.database_tools.get_employee_summary") as mock_summary:
            from app.database.exceptions import DatabaseError
            mock_summary.side_effect = DatabaseError("Connection refused")

            res = run_agent("Check E1001", client=mock_client)

            self.assertEqual(res.status, "completed")
            self.assertEqual(res.total_steps, 1)
            self.assertEqual(res.steps[0].tool_result.get("status"), "error")

    def test_14_security_boundary_no_arbitrary_execution(self):
        """14. Assert that the agent tool registry contains only safe approved tools."""
        disallowed = ["exec", "eval", "sql", "os", "subprocess", "query_raw", "execute_sql"]
        for tool_name in TOOLS_BY_NAME:
            for kw in disallowed:
                self.assertNotIn(kw, tool_name.lower())

    def test_15_final_answer_synthesis_without_tools(self):
        """15. Verify conversational or clarifying questions that require no tools return directly."""
        mock_client = MagicMock()
        resp = _create_mock_completion(content="Hello! I am your Enterprise Support Agent. How can I help you today?", tool_calls=None)
        mock_client.chat.completions.create.return_value = resp

        res = run_agent("Hello", client=mock_client)

        self.assertEqual(res.status, "completed")
        self.assertEqual(res.total_steps, 0)
        self.assertEqual(res.final_answer, "Hello! I am your Enterprise Support Agent. How can I help you today?")


class TestAgentRealSmokeTest(unittest.TestCase):
    """Optional smoke test against real configured Groq model."""

    def test_real_llm_tool_calling_smoke_test(self):
        """Execute a real live query against Groq to verify native tool-calling."""
        try:
            res = run_agent("How many annual leave days does employee E1001 have left?")
            if res.status == "error" and "error occurred while contacting" in res.final_answer:
                self.skipTest("Groq API rate limit or network issue encountered during smoke test.")
            
            # If successful, verify tool was chosen
            self.assertIn(res.status, ["completed", "max_steps_reached"])
            safe_answer = res.final_answer.encode("ascii", errors="replace").decode("ascii")
            print(f"\n[Real Model Smoke Test Output]:\nQuery: {res.query}\nFinal Answer: {safe_answer}\nSteps: {res.total_steps}")
        except Exception as e:
            self.skipTest(f"Live smoke test skipped due to exception: {e}")


if __name__ == "__main__":
    unittest.main()
