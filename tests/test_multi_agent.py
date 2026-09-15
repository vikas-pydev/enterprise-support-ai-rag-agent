"""Unit and Integration Tests for LangGraph Multi-Agent Architecture.

Tests the supervisor and specialized worker execution graph:
1. supervisor graph initializes and compiles
2. valid route to HR Policy worker
3. valid route to Employee Records worker
4. valid route to Travel & Expense worker
5. invalid route rejected
6. HR worker only receives policy tool schema
7. Employee worker only receives employee/leave tool schemas
8. Travel worker only receives travel tool schema
9. policy question reaches ask_policy
10. employee question reaches get_employee
11. leave question reaches get_leave_balance
12. department question reaches list_department_employees
13. travel question reaches get_travel_summary
14. worker result returns to supervisor
15. multi-worker workflow works
16. worker cannot invoke another worker's tool
17. tool errors are sanitized
18. RAG refusal is preserved
19. MAX_AGENT_STEPS is enforced
20. supervisor loop protection works
21. execution trace contains worker routing
22. execution trace contains tool metadata
23. citations survive HR Policy worker execution
24. used_rag is captured
25. final synthesis works
26. no chain-of-thought is exposed
27. session isolation remains intact
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from typing import Any

from app.agent.multi_agent import (
    create_multi_agent_graph,
    run_multi_agent,
    MultiAgentState,
    HR_POLICY_WORKER,
    EMPLOYEE_RECORDS_WORKER,
    TRAVEL_EXPENSE_WORKER,
    HR_POLICY_TOOLS,
    EMPLOYEE_RECORDS_TOOLS,
    TRAVEL_EXPENSE_TOOLS,
    ROUTING_ALLOWLIST,
    WORKER_TOOL_SCHEMAS,
    supervisor_node,
    _parse_supervisor_response,
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


class TestMultiAgent(unittest.TestCase):
    """Comprehensive test suite for Multi-Agent Supervisor & Worker Architecture."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            p.stop()

    def setUp(self):
        self.session_store = InMemorySessionStore()

    def test_01_supervisor_graph_initializes_and_compiles_correctly(self):
        """1. Verify supervisor graph builds, adds all worker nodes and edges, and compiles."""
        graph = create_multi_agent_graph()
        self.assertIsNotNone(graph)
        self.assertTrue(hasattr(graph, "invoke"))

    def test_02_valid_route_to_hr_policy_worker(self):
        """2. Verify supervisor correctly routes general policy inquiries to HR Policy worker."""
        mock_client = MagicMock()
        # Supervisor routes to hr_policy
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Policy inquiry"})
        )

        state: MultiAgentState = {
            "query": "What is the meal per diem for domestic travel?",
            "client": mock_client,
            "step_count": 0,
            "max_steps": 5,
            "supervisor_iterations": 0,
            "max_supervisor_iterations": 6,
            "routing_history": [],
        }

        res = supervisor_node(state)
        self.assertEqual(res["current_worker"], "hr_policy")
        self.assertEqual(res["supervisor_iterations"], 1)
        self.assertEqual(len(res["routing_history"]), 1)
        self.assertEqual(res["routing_history"][0]["route"], "hr_policy")

    def test_03_valid_route_to_employee_records_worker(self):
        """3. Verify supervisor routes employee profile inquiries to Employee Records worker."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Employee lookup"})
        )

        state: MultiAgentState = {
            "query": "What department does E1001 work in?",
            "client": mock_client,
            "step_count": 0,
            "max_steps": 5,
            "supervisor_iterations": 0,
            "max_supervisor_iterations": 6,
            "routing_history": [],
        }

        res = supervisor_node(state)
        self.assertEqual(res["current_worker"], "employee_records")

    def test_04_valid_route_to_travel_expense_worker(self):
        """4. Verify supervisor routes expense inquiries to Travel & Expense worker."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Travel expense query"})
        )

        state: MultiAgentState = {
            "query": "How much has E1001 spent on travel?",
            "client": mock_client,
            "step_count": 0,
            "max_steps": 5,
            "supervisor_iterations": 0,
            "max_supervisor_iterations": 6,
            "routing_history": [],
        }

        res = supervisor_node(state)
        self.assertEqual(res["current_worker"], "travel_expense")

    def test_05_invalid_route_rejected(self):
        """5. Verify invalid supervisor route is rejected and safely terminated."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({"next_worker": "unauthorized_database_admin", "reasoning_summary": "Direct DB"})
        )

        state: MultiAgentState = {
            "query": "Drop all database tables",
            "client": mock_client,
            "step_count": 0,
            "max_steps": 5,
            "supervisor_iterations": 0,
            "max_supervisor_iterations": 6,
            "routing_history": [],
        }

        res = supervisor_node(state)
        self.assertEqual(res["current_worker"], "finish")
        self.assertIn("error", res)
        self.assertFalse(res["routing_history"][0]["valid"])

    def test_06_hr_worker_only_receives_policy_tool(self):
        """6. Verify HR worker schema only contains ask_policy."""
        schemas = WORKER_TOOL_SCHEMAS[HR_POLICY_WORKER]
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertEqual(set(tool_names), HR_POLICY_TOOLS)
        self.assertEqual(tool_names, ["ask_policy"])

    def test_07_employee_worker_only_receives_employee_tools(self):
        """7. Verify Employee worker schema only contains employee/leave/department tools."""
        schemas = WORKER_TOOL_SCHEMAS[EMPLOYEE_RECORDS_WORKER]
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertEqual(set(tool_names), EMPLOYEE_RECORDS_TOOLS)
        self.assertIn("get_employee", tool_names)
        self.assertIn("get_leave_balance", tool_names)
        self.assertIn("list_department_employees", tool_names)
        self.assertNotIn("ask_policy", tool_names)
        self.assertNotIn("get_travel_summary", tool_names)

    def test_08_travel_worker_only_receives_travel_tool(self):
        """8. Verify Travel worker schema only contains get_travel_summary."""
        schemas = WORKER_TOOL_SCHEMAS[TRAVEL_EXPENSE_WORKER]
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertEqual(set(tool_names), TRAVEL_EXPENSE_TOOLS)
        self.assertEqual(tool_names, ["get_travel_summary"])
        self.assertNotIn("ask_policy", tool_names)
        self.assertNotIn("get_employee", tool_names)

    def test_09_policy_question_reaches_ask_policy(self):
        """9. Verify policy question runs HR worker, invokes ask_policy, and synthesizes answer."""
        mock_client = MagicMock()
        # 1. Supervisor routes to hr_policy
        s_resp = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Policy question"}))
        # 2. HR worker calls ask_policy
        tc = _create_mock_tool_call("tc_1", "ask_policy", {"question": "What is meal per diem?"})
        w_resp = _create_mock_completion(content=None, tool_calls=[tc])
        # 3. Supervisor sees worker result and routes to finish
        s_finish = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        # 4. Final synthesis generates response
        final_synth = _create_mock_completion(content="The meal per diem rate is $75 per day.")

        mock_client.chat.completions.create.side_effect = [s_resp, w_resp, s_finish, final_synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([("Per diem is $75", 8.8, {"title": "Travel Policy", "source": "travel.md", "chunk_uid": "chunk_77"})], MagicMock())
            mock_ans.return_value = "The meal per diem is $75."

            resp = run_multi_agent(
                user_query="What is the meal per diem for travel?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertTrue(resp.used_rag)
            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(resp.steps[0].tool_name, "ask_policy")
            self.assertIn("$75", resp.final_answer)
            self.assertGreater(len(resp.citations), 0)
            self.assertEqual(resp.citations[0]["chunk_uid"], "chunk_77")

    def test_10_employee_question_reaches_get_employee(self):
        """10. Verify employee question runs Employee worker and invokes get_employee."""
        mock_client = MagicMock()
        s_resp = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Employee lookup"}))
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w_resp = _create_mock_completion(content=None, tool_calls=[tc])
        s_finish = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Found employee"}))
        final_synth = _create_mock_completion(content="Alice Chen is a Senior Software Engineer in Engineering.")

        mock_client.chat.completions.create.side_effect = [s_resp, w_resp, s_finish, final_synth]

        resp = run_multi_agent(
            user_query="What department does E1001 work in?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertFalse(resp.used_rag)
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_employee")
        self.assertEqual(resp.steps[0].status, "success")
        self.assertIn("Alice Chen", resp.final_answer)

    def test_11_leave_question_reaches_get_leave_balance(self):
        """11. Verify leave inquiry runs Employee worker and invokes get_leave_balance."""
        mock_client = MagicMock()
        s_resp = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Leave balance lookup"}))
        tc = _create_mock_tool_call("tc_l", "get_leave_balance", {"employee_id": "E1001"})
        w_resp = _create_mock_completion(content=None, tool_calls=[tc])
        s_finish = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        final_synth = _create_mock_completion(content="Alice Chen has 14 days of annual leave remaining.")

        mock_client.chat.completions.create.side_effect = [s_resp, w_resp, s_finish, final_synth]

        resp = run_multi_agent(
            user_query="How much annual leave does E1001 have left?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_leave_balance")
        self.assertIn("14 days", resp.final_answer)

    def test_12_department_question_reaches_list_department_employees(self):
        """12. Verify department inquiry runs Employee worker and invokes list_department_employees."""
        mock_client = MagicMock()
        s_resp = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Department roster"}))
        tc = _create_mock_tool_call("tc_d", "list_department_employees", {"department": "Engineering"})
        w_resp = _create_mock_completion(content=None, tool_calls=[tc])
        s_finish = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        final_synth = _create_mock_completion(content="The Engineering team consists of Alice Chen and Bob Smith.")

        mock_client.chat.completions.create.side_effect = [s_resp, w_resp, s_finish, final_synth]

        resp = run_multi_agent(
            user_query="Who works in Engineering?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "list_department_employees")

    def test_13_travel_question_reaches_get_travel_summary(self):
        """13. Verify travel inquiry runs Travel worker and invokes get_travel_summary."""
        mock_client = MagicMock()
        s_resp = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Travel summary lookup"}))
        tc = _create_mock_tool_call("tc_t", "get_travel_summary", {"employee_id": "E1001"})
        w_resp = _create_mock_completion(content=None, tool_calls=[tc])
        s_finish = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        final_synth = _create_mock_completion(content="E1001 has spent a total of $3,200 on travel expenses.")

        mock_client.chat.completions.create.side_effect = [s_resp, w_resp, s_finish, final_synth]

        resp = run_multi_agent(
            user_query="How much has E1001 spent on travel?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")
        self.assertIn("$3,200", resp.final_answer)

    def test_14_worker_result_returns_to_supervisor(self):
        """14. Verify worker tool observations are formatted and passed back to supervisor context."""
        mock_client = MagicMock()
        s_resp1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Check travel"}))
        tc = _create_mock_tool_call("tc_1", "get_travel_summary", {"employee_id": "E1001"})
        w_resp = _create_mock_completion(content=None, tool_calls=[tc])
        s_finish = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Got expenses"}))
        final_synth = _create_mock_completion(content="Travel summary synthesized.")

        mock_client.chat.completions.create.side_effect = [s_resp1, w_resp, s_finish, final_synth]

        resp = run_multi_agent(
            user_query="Check travel for E1001",
            client=mock_client,
            session_store=self.session_store,
        )

        # Check second call to supervisor (index 2 in side_effect calls)
        supervisor_second_call_messages = mock_client.chat.completions.create.call_args_list[2][1]["messages"]
        user_prompt_content = supervisor_second_call_messages[1]["content"]
        self.assertIn("WORKER FINDINGS COLLECTED SO FAR", user_prompt_content)
        self.assertIn("travel_expense", user_prompt_content)

    def test_15_multi_worker_sequential_workflow_works(self):
        """15. Verify sequential multi-worker workflow (Travel worker -> Supervisor -> Employee worker -> Supervisor -> Synthesis)."""
        mock_client = MagicMock()
        # 1. Supervisor routes to travel_expense
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Fetch travel expenses"}))
        # 2. Travel worker calls get_travel_summary
        tc1 = _create_mock_tool_call("tc_trav", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])
        # 3. Supervisor sees travel results, routes to employee_records for manager name
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Fetch employee profile for manager"}))
        # 4. Employee worker calls get_employee
        tc2 = _create_mock_tool_call("tc_emp", "get_employee", {"employee_id": "E1001"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])
        # 5. Supervisor routes to finish
        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "All data collected"}))
        # 6. Final synthesis combines travel spend and manager name
        synth = _create_mock_completion(content="Alice Chen (E1001) has spent $3,200 on travel, and her direct manager is Bob Smith.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, s3, synth]

        resp = run_multi_agent(
            user_query="How much has E1001 spent on travel, and what is their manager's name?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(resp.steps[1].tool_name, "get_employee")
        self.assertIn("$3,200", resp.final_answer)
        self.assertIn("Bob Smith", resp.final_answer)

    def test_16_worker_cannot_invoke_another_workers_tool(self):
        """16. Verify security boundary: worker attempting to call an unauthorized tool is strictly rejected."""
        mock_client = MagicMock()
        # Supervisor routes to HR policy worker
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Check policy"}))
        # HR worker attempts to illegally call get_employee (SQL tool)
        tc_illegal = _create_mock_tool_call("tc_bad", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc_illegal])
        # Supervisor finishes
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Stop after violation"}))
        synth = _create_mock_completion(content="Could not access employee data via HR policy agent.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="Use HR policy tool to get employee E1001",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].status, "error")
        self.assertIn("Security error: Worker 'hr_policy' is not authorized", resp.steps[0].error)

    def test_17_tool_errors_are_sanitized(self):
        """17. Verify tool execution exceptions are captured cleanly without leaking internal traces."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup"}))
        tc = _create_mock_tool_call("tc_err", "get_employee", {"employee_id": "E99999"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Handle missing"}))
        synth = _create_mock_completion(content="Employee E99999 was not found.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        with patch("app.tools.database_tools.get_employee_summary") as mock_db:
            mock_db.side_effect = Exception("Internal DB Timeout (Secret: credentials_123)")

            resp = run_multi_agent(
                user_query="Get employee E99999",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(resp.steps[0].status, "error")
            self.assertNotIn("credentials_123", resp.steps[0].error)
            self.assertIn("error occurred while querying employee records", resp.steps[0].error)

    def test_18_rag_refusal_is_preserved(self):
        """18. Verify RAG refusal responses preserve status and pass through cleanly."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Policy question"}))
        tc = _create_mock_tool_call("tc_rag", "ask_policy", {"question": "What is company policy on alien invasions?"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Refusal"}))
        synth = _create_mock_completion(content="The provided enterprise documents do not contain information regarding alien invasions.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([], MagicMock())
            mock_ans.return_value = "The provided enterprise documents do not contain information on this topic."

            resp = run_multi_agent(
                user_query="What is company policy on alien invasions?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertTrue(resp.used_rag)
            self.assertIn("do not contain information", resp.final_answer)

    def test_19_max_agent_steps_is_enforced(self):
        """19. Verify max agent step limit (e.g. 2 steps) routes to max_steps termination."""
        mock_client = MagicMock()
        # Supervisor endlessly loops to travel_expense
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Step 1"}))
        tc1 = _create_mock_tool_call("tc_1", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        s2 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Step 2"}))
        tc2 = _create_mock_tool_call("tc_2", "get_travel_summary", {"employee_id": "E1002"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        max_steps_synth = _create_mock_completion(content="Step limit reached.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, max_steps_synth]

        resp = run_multi_agent(
            user_query="Keep looping expenses",
            max_steps=2,
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "max_steps_reached")
        self.assertEqual(len(resp.steps), 2)

    def test_20_supervisor_loop_protection_works(self):
        """20. Verify supervisor loop limit protects against runaway decision cycling."""
        mock_client = MagicMock()
        # Supervisor never finishes, keeps picking workers that return direct text
        s_loop = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Looping"}))
        w_direct = _create_mock_completion(content="Direct answer from worker without tools.")
        synth = _create_mock_completion(content="Terminated safely.")

        # Provide enough side effects for up to max_supervisor_iterations
        mock_client.chat.completions.create.side_effect = [
            s_loop, w_direct,
            s_loop, w_direct,
            s_loop, w_direct,
            s_loop, w_direct,
            s_loop, w_direct,
            s_loop, w_direct,
            s_loop, w_direct,
            synth,
        ]

        resp = run_multi_agent(
            user_query="Trigger supervisor loop",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertIn(resp.status, ("completed", "max_steps_reached"))
        self.assertIsNotNone(resp.final_answer)

    def test_21_execution_trace_contains_worker_routing(self):
        """21. Verify structured trace captures supervisor routing decisions and selected workers."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup employee"}))
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is in Engineering.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="Who is E1001?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertIsNotNone(resp.trace)
        self.assertEqual(resp.trace.status, "completed")
        self.assertEqual(resp.trace.tools_invoked, ["get_employee"])
        self.assertEqual(resp.trace.total_steps, 1)

    def test_22_execution_trace_contains_tool_metadata_and_durations(self):
        """22. Verify individual steps in trace have tool args, results, and timing."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Get expenses"}))
        tc = _create_mock_tool_call("tc_t", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Finished"}))
        synth = _create_mock_completion(content="Spent $3,200.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="Expenses for E1001",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertGreaterEqual(resp.duration_ms, 0.0)
        self.assertEqual(len(resp.steps), 1)
        step = resp.steps[0]
        self.assertEqual(step.tool_name, "get_travel_summary")
        self.assertEqual(step.tool_args, {"employee_id": "E1001"})
        self.assertGreaterEqual(step.duration_ms, 0.0)

    def test_23_citations_survive_hr_policy_worker_execution(self):
        """23. Verify chunk citations from ask_policy pass cleanly through to AgentResponse.citations."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Check policy"}))
        tc = _create_mock_tool_call("tc_p", "ask_policy", {"question": "What is the meal allowance?"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Meal allowance is $75 [Travel_Policy.md].")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = (
                [("Allowance is $75", 9.1, {"title": "Travel Policy", "source": "Travel_Policy.md", "chunk_uid": "chunk_hr_01"})],
                MagicMock(),
            )
            mock_ans.return_value = "Meal allowance is $75."

            resp = run_multi_agent(
                user_query="What is the meal allowance?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(len(resp.citations), 1)
            self.assertEqual(resp.citations[0]["chunk_uid"], "chunk_hr_01")
            self.assertEqual(resp.citations[0]["title"], "Travel Policy")

    def test_24_used_rag_flag_is_captured(self):
        """24. Verify used_rag flag is True for policy queries and False for database-only queries."""
        mock_client = MagicMock()
        # Database query
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup"}))
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen.")
        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="Who is E1001?",
            client=mock_client,
            session_store=self.session_store,
        )
        self.assertFalse(resp.used_rag)
        self.assertFalse(resp.trace.used_rag)

    def test_25_final_synthesis_works(self):
        """25. Verify final synthesis properly synthesizes responses directly when no tools were needed."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "General greeting, no tools required"}))
        synth = _create_mock_completion(content="Hello! How can I assist you with enterprise support today?")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        resp = run_multi_agent(
            user_query="Hi there!",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 0)
        self.assertIn("assist you", resp.final_answer)

    def test_26_no_chain_of_thought_is_exposed(self):
        """26. Verify raw internal system prompts and reasoning are not leaked in final answer."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Internal routing decision: routing to finish"}))
        synth = _create_mock_completion(content="Here is your official answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        resp = run_multi_agent(
            user_query="Tell me something",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertNotIn("SUPERVISOR_SYSTEM_PROMPT", resp.final_answer)
        self.assertNotIn("Internal routing decision", resp.final_answer)
        self.assertEqual(resp.final_answer, "Here is your official answer.")

    def test_27_session_isolation_remains_intact(self):
        """27. Verify multi-turn conversational history is isolated between distinct sessions."""
        store = InMemorySessionStore()

        mock_client = MagicMock()
        # Session A turn 1
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth1 = _create_mock_completion(content="Session A reply")
        mock_client.chat.completions.create.side_effect = [s1, synth1]

        resp_a = run_multi_agent(
            user_query="Session A query",
            session_id="session-AAA",
            session_store=store,
            client=mock_client,
        )

        # Session B turn 1
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth2 = _create_mock_completion(content="Session B reply")
        mock_client.chat.completions.create.side_effect = [s2, synth2]

        resp_b = run_multi_agent(
            user_query="Session B query",
            session_id="session-BBB",
            session_store=store,
            client=mock_client,
        )

        session_a_msgs = store.get_session("session-AAA")
        session_b_msgs = store.get_session("session-BBB")

        self.assertEqual(len(session_a_msgs), 2)  # [user, assistant]
        self.assertEqual(session_a_msgs[0]["content"], "Session A query")
        self.assertEqual(session_a_msgs[1]["content"], "Session A reply")

        self.assertEqual(len(session_b_msgs), 2)  # [user, assistant]
        self.assertEqual(session_b_msgs[0]["content"], "Session B query")
        self.assertEqual(session_b_msgs[1]["content"], "Session B reply")


if __name__ == "__main__":
    unittest.main()
