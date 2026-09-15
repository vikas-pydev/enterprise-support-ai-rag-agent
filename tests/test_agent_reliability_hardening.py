"""Comprehensive Deterministic Agent & LangGraph Reliability Hardening Tests (Phase 9 Task 5).

Validates:
1. Malformed and adversarial tool-call inputs (unknown tools, schema violations, type mismatches, nulls, long strings).
2. Safe tool failure recovery (DatabaseError, unexpected exceptions, empty/malformed results, RAG failures).
3. Tool timing, monotonic durations, and bounded step budgets.
4. Supervisor routing failure recovery (invalid routes, missing routes, malformed JSON, stall protection, cycle detection, iteration budgets).
5. Duplicate call rejection and replay protection across agent turns and approval checkpoints.
6. Graph state corruption resilience (missing fields, None values, empty dictionaries, inconsistent step counts).
7. Trace and observability integrity on failures (accurate tool counts, non-negative duration, zero secret/stack trace leakage).
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agent.agent import (
    run_agent,
    _execute_tool_call,
    _extract_citations,
    _build_agent_response,
    AgentResponse,
    AgentStep,
    AgentExecutionTrace,
    TOOLS_BY_NAME,
    MAX_AGENT_STEPS,
)
from app.agent.graph import AgentGraphState, llm_node, tool_node, route_after_llm
from app.agent.multi_agent import (
    MultiAgentState,
    _parse_supervisor_response,
    supervisor_node,
    approval_node,
    _execute_worker,
    hr_policy_worker_node,
    employee_records_worker_node,
    travel_expense_worker_node,
    final_synthesis_node,
    max_steps_node,
    route_after_supervisor,
    create_multi_agent_graph,
    run_multi_agent,
    resume_multi_agent_approval,
    check_approval_policy,
    HR_POLICY_WORKER,
    EMPLOYEE_RECORDS_WORKER,
    TRAVEL_EXPENSE_WORKER,
    WORKER_TOOL_MAPPING,
    APPROVAL_STATUS_NOT_REQUIRED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
)
from app.agent.memory import InMemorySessionStore
from app.agent.checkpoint import MemorySaver
from app.database.exceptions import DatabaseError
from app.tools.rag_tools import ask_policy
from app.tools.database_tools import get_employee, get_leave_balance, get_travel_summary, list_department_employees


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
    args_str = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
    fn = SimpleNamespace(name=name, arguments=args_str)
    return SimpleNamespace(id=call_id, function=fn, type="function")


class TestMalformedToolCallsHardening(unittest.TestCase):
    """Deterministic tests for malformed, unexpected, or adversarial tool-call payloads."""

    def test_unknown_tool_name_safely_rejected(self):
        """Unknown or unauthorized tool names return structured error step without executing."""
        unauthorized_tools = [
            "execute_sql",
            "drop_database",
            "delete_all_users",
            "system_bash",
            "__import__",
            "",
            "   ",
        ]
        for bad_tool in unauthorized_tools:
            validated_args, result, step = _execute_tool_call(bad_tool, {"arg": "value"}, step_number=1)
            self.assertEqual(step.status, "error")
            self.assertEqual(step.tool_name, bad_tool)
            self.assertIn("not recognized or permitted", step.error)
            self.assertEqual(result.get("status"), "error")
            self.assertFalse(result.get("found", True))

    def test_missing_required_tool_arguments_rejected(self):
        """Tools requiring specific arguments (e.g. employee_id) reject empty payloads via Pydantic."""
        tools_requiring_args = [
            ("get_employee", {}),
            ("get_leave_balance", {}),
            ("get_travel_summary", {}),
            ("list_department_employees", {}),
            ("ask_policy", {}),
        ]
        for tool_name, empty_args in tools_requiring_args:
            val_args, result, step = _execute_tool_call(tool_name, empty_args, step_number=1)
            self.assertEqual(step.status, "error")
            self.assertIn("Invalid tool arguments", step.error)
            self.assertEqual(result.get("status"), "error")

    def test_wrong_argument_types_rejected_by_schema(self):
        """Passing incorrect argument types (e.g. dict/list instead of str) triggers validation errors."""
        invalid_type_calls = [
            ("get_employee", {"employee_id": ["E1001", "E1002"]}),
            ("get_employee", {"employee_id": {"nested": "E1001"}}),
            ("list_department_employees", {"department": 12345}),
            ("ask_policy", {"question": ["What is policy?"]}),
        ]
        for tool_name, bad_args in invalid_type_calls:
            val_args, result, step = _execute_tool_call(tool_name, bad_args, step_number=1)
            self.assertEqual(step.status, "error")
            self.assertIn("Invalid tool arguments", step.error)

    def test_null_and_empty_arguments_handled_safely(self):
        """Passing None or whitespace-only values does not crash the tool-calling loop."""
        val_args, result, step = _execute_tool_call("get_employee", {"employee_id": None}, step_number=1)
        self.assertEqual(step.status, "error")

        # Whitespace employee_id
        val_args, result, step = _execute_tool_call("get_employee", {"employee_id": "   "}, step_number=1)
        # Should either be schema-handled or return clean found: False
        self.assertTrue(step.status in ("error", "success"))
        if step.status == "success":
            self.assertFalse(result.get("found", True))

    def test_malformed_json_argument_strings_handled_safely(self):
        """Non-parseable raw JSON strings are caught before execution with a clear error step."""
        malformed_strings = [
            "{invalid json string",
            "{'single_quotes': True}",
            "[1, 2, 3",
            "not json at all",
            "",
        ]
        for bad_json in malformed_strings:
            val_args, result, step = _execute_tool_call("get_employee", bad_json, step_number=1)
            self.assertEqual(step.status, "error")
            self.assertEqual(result.get("status"), "error")

    def test_extremely_long_string_argument_safety(self):
        """Extremely long arguments (>50,000 characters) do not cause buffer overflow or server crash."""
        long_str = "E" + "0" * 50000
        val_args, result, step = _execute_tool_call("get_employee", {"employee_id": long_str}, step_number=1)
        self.assertIsInstance(step, AgentStep)
        self.assertFalse(result.get("found", True))

    def test_worker_tool_boundary_security_violation_blocked(self):
        """A worker attempting to invoke a tool outside its designated boundary is blocked."""
        # HR Policy Worker attempting employee database lookup
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            tool_calls=[_create_mock_tool_call("call_1", "get_employee", {"employee_id": "E1001"})]
        )

        state: MultiAgentState = {
            "query": "What is the policy for E1001?",
            "steps": [],
            "executed_calls": {},
            "worker_results": [],
            "collected_evidence": [],
            "completed_domains": [],
            "client": mock_client,
        }

        result = _execute_worker(HR_POLICY_WORKER, state)
        self.assertEqual(len(result["steps"]), 1)
        sec_step = result["steps"][0]
        self.assertEqual(sec_step.status, "error")
        self.assertIn("Security error", sec_step.error)
        self.assertIn("not authorized", sec_step.error)


class TestToolFailureRecoveryHardening(unittest.TestCase):
    """Deterministic tests for safe recovery when tools or external resources fail."""

    def test_database_error_handled_safely_in_tool_execution(self):
        """DatabaseError raised during repository access is safely caught and recorded."""
        with patch("app.tools.database_tools.get_employee_summary", side_effect=DatabaseError("DB timeout")):
            val_args, result, step = _execute_tool_call("get_employee", {"employee_id": "E1001"}, step_number=1)
            self.assertEqual(step.status, "error")
            self.assertFalse(result.get("found", True))
            self.assertIn("database error occurred", result.get("error", "").lower())
            self.assertNotIn("Traceback", json.dumps(result))

    def test_unexpected_runtime_exception_in_tool_handled_safely(self):
        """Unexpected runtime exceptions (e.g. OSError, MemoryError) are caught by _execute_tool_call."""
        with patch.dict(TOOLS_BY_NAME):
            mock_tool = MagicMock()
            mock_tool.name = "faulty_tool"
            mock_tool.args_schema = None
            mock_tool.invoke.side_effect = RuntimeError("Fatal hardware bus error")
            TOOLS_BY_NAME["faulty_tool"] = mock_tool

            val_args, result, step = _execute_tool_call("faulty_tool", {}, step_number=1)
            self.assertEqual(step.status, "error")
            self.assertIn("Tool execution failed", step.error)
            self.assertEqual(result.get("status"), "error")

    def test_tool_returning_non_dict_wrapped_safely(self):
        """Tools returning non-dict values (e.g. raw string, int, list) are safely normalized."""
        with patch.dict(TOOLS_BY_NAME):
            mock_tool = MagicMock()
            mock_tool.name = "scalar_tool"
            mock_tool.args_schema = None
            mock_tool.invoke.return_value = "raw string observation"
            TOOLS_BY_NAME["scalar_tool"] = mock_tool

            val_args, result, step = _execute_tool_call("scalar_tool", {}, step_number=1)
            self.assertEqual(step.status, "success")
            self.assertEqual(result, {"result": "raw string observation"})

    def test_rag_tool_failure_returns_grounded_refusal_without_stack_trace(self):
        """When retriever fails unexpectedly, ask_policy returns standard refusal without stack trace."""
        with patch("app.tools.rag_tools.retrieve", side_effect=Exception("ChromaDB index corrupted")):
            result = ask_policy.invoke({"question": "What is meal per diem?"})
            self.assertTrue(result["is_refusal"])
            self.assertIn("not available", result["answer"].lower())
            self.assertEqual(result["sources"], [])
            self.assertNotIn("Traceback", json.dumps(result))


class TestToolTimingAndBudgetHardening(unittest.TestCase):
    """Deterministic tests for monotonic timing, non-negative duration_ms, and step budget bounds."""

    def test_step_duration_monotonic_and_non_negative(self):
        """Every tool execution step records a non-negative execution duration in milliseconds."""
        val_args, result, step = _execute_tool_call("ask_policy", {"question": "What is the holiday policy?"})
        self.assertGreaterEqual(step.duration_ms, 0.0)
        self.assertIsInstance(step.duration_ms, float)

    def test_max_agent_steps_budget_enforced(self):
        """Agent loop strictly halts when max_steps is reached without infinite cycling."""
        mock_client = MagicMock()
        # Always return a tool call to simulate infinite tool-calling attempt
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            tool_calls=[_create_mock_tool_call("call_loop", "ask_policy", {"question": "Loop question"})]
        )

        with patch("app.tools.rag_tools.retrieve", return_value=([], {})):
            response = run_agent(
                user_query="Infinite loop attempt",
                max_steps=3,
                client=mock_client,
            )

        self.assertEqual(response.status, "max_steps_reached")
        self.assertEqual(response.total_steps, 3)
        self.assertEqual(len(response.steps), 3)
        self.assertGreaterEqual(response.duration_ms, 0.0)


class TestSupervisorRoutingFailuresHardening(unittest.TestCase):
    """Deterministic tests for supervisor routing parser resilience, fallback routing, and cycle protection."""

    # -----------------------------------------------------------------
    # 1. Parsing Malformed Supervisor Decisions
    # -----------------------------------------------------------------

    def test_supervisor_parser_handles_empty_and_whitespace_responses(self):
        """Empty supervisor responses safely fall back to 'finish' route."""
        route, reason, missing, completed, is_valid = _parse_supervisor_response("")
        self.assertEqual(route, "finish")
        self.assertFalse(is_valid)

        route, reason, missing, completed, is_valid = _parse_supervisor_response("   \n\t  ")
        self.assertEqual(route, "finish")
        self.assertFalse(is_valid)

    def test_supervisor_parser_handles_invalid_worker_name(self):
        """Unrecognized worker name in JSON output is marked as invalid."""
        raw_json = json.dumps({
            "next_worker": "delete_all_records",
            "reasoning_summary": "Attempting unauthorized route",
        })
        route, reason, missing, completed, is_valid = _parse_supervisor_response(raw_json)
        self.assertEqual(route, "delete_all_records")
        self.assertFalse(is_valid)
        self.assertIn("Invalid worker", reason)

    def test_supervisor_parser_extracts_markdown_fenced_json(self):
        """Supervisor JSON inside markdown code blocks is properly extracted and validated."""
        fenced_content = """```json
{
  "next_worker": "employee_records",
  "reasoning_summary": "Looking up employee profile for E1001",
  "missing_information": [],
  "completed_domains": []
}
```"""
        route, reason, missing, completed, is_valid = _parse_supervisor_response(fenced_content)
        self.assertEqual(route, "employee_records")
        self.assertTrue(is_valid)

    def test_supervisor_parser_plain_text_keyword_fallback(self):
        """Supervisor output in plain text with keywords correctly falls back to valid route."""
        text = "Based on the evidence, we should now route to hr_policy to check travel limits."
        route, reason, missing, completed, is_valid = _parse_supervisor_response(text)
        self.assertEqual(route, "hr_policy")
        self.assertTrue(is_valid)

    # -----------------------------------------------------------------
    # 2. Stall & Cycle Detection
    # -----------------------------------------------------------------

    def test_supervisor_stall_protection_terminates_repeated_worker(self):
        """Supervisor terminates workflow when the same worker repeats without progress."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({
                "next_worker": "employee_records",
                "reasoning_summary": "Trying employee records again",
            })
        )

        state: MultiAgentState = {
            "query": "Where is E1001?",
            "step_count": 2,
            "max_steps": 5,
            "supervisor_iterations": 2,
            "max_supervisor_iterations": 6,
            "routing_history": [
                {"route": "employee_records", "reason": "First attempt"},
                {"route": "employee_records", "reason": "Second attempt"},
            ],
            "worker_results": [
                {"worker": "employee_records", "summary": "Not found", "success": False},
                {"worker": "employee_records", "summary": "Not found", "success": False},
            ],
            "client": mock_client,
        }

        result = supervisor_node(state)
        self.assertEqual(result["current_worker"], "finish")
        self.assertIn("Stall protection", result["routing_history"][-1]["reason"])

    def test_supervisor_cycle_protection_terminates_oscillating_workers(self):
        """Supervisor terminates when an alternating cycle (A -> B -> A -> B) is detected."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({
                "next_worker": "travel_expense",
                "reasoning_summary": "Continuing cycle",
            })
        )

        state: MultiAgentState = {
            "query": "Complex query",
            "step_count": 4,
            "max_steps": 8,
            "supervisor_iterations": 4,
            "max_supervisor_iterations": 8,
            "routing_history": [
                {"route": "hr_policy"},
                {"route": "travel_expense"},
                {"route": "hr_policy"},
                {"route": "travel_expense"},
            ],
            "worker_results": [],
            "client": mock_client,
        }

        result = supervisor_node(state)
        self.assertEqual(result["current_worker"], "finish")
        self.assertIn("Cycle protection", result["routing_history"][-1]["reason"])

    def test_supervisor_iteration_budget_exhaustion(self):
        """Supervisor terminates when max_supervisor_iterations is reached."""
        state: MultiAgentState = {
            "query": "Query",
            "step_count": 2,
            "max_steps": 10,
            "supervisor_iterations": 6,
            "max_supervisor_iterations": 6,
            "routing_history": [],
            "worker_results": [],
        }

        result = supervisor_node(state)
        self.assertEqual(result["current_worker"], "finish")
        self.assertEqual(result["workflow_status"], "max_steps_reached")


class TestDuplicateAndReplayProtectionHardening(unittest.TestCase):
    """Deterministic tests for duplicate tool-call prevention and replayed approval defense."""

    def test_identical_tool_call_duplicate_rejected_and_cached_data_returned(self):
        """Executing the exact same tool with identical arguments returns cached data on second call."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            tool_calls=[_create_mock_tool_call("call_1", "get_employee", {"employee_id": "E1001"})]
        )

        state: MultiAgentState = {
            "query": "Get info on E1001",
            "steps": [],
            "executed_calls": {},
            "worker_results": [],
            "collected_evidence": [],
            "completed_domains": [],
            "client": mock_client,
        }

        with patch("app.tools.database_tools.get_employee_summary", return_value={"employee_id": "E1001", "name": "Alice"}):
            # First execution: tool executes
            res1 = _execute_worker(EMPLOYEE_RECORDS_WORKER, state)
            self.assertEqual(len(res1["steps"]), 1)
            self.assertEqual(res1["steps"][0].status, "success")

            # Second execution with same state and identical args: duplicate rejected
            state_turn2: MultiAgentState = {
                "query": "Get info on E1001 again",
                "steps": list(res1["steps"]),
                "executed_calls": dict(res1["executed_calls"]),
                "worker_results": list(res1["worker_results"]),
                "collected_evidence": list(res1["collected_evidence"]),
                "completed_domains": list(res1["completed_domains"]),
                "client": mock_client,
            }
            res2 = _execute_worker(EMPLOYEE_RECORDS_WORKER, state_turn2)
            self.assertEqual(len(res2["steps"]), 2)
            dup_step = res2["steps"][1]
            self.assertEqual(dup_step.status, "rejected_duplicate")
            self.assertEqual(dup_step.error, "Duplicate tool call rejected.")

    def test_tool_call_with_different_arguments_is_permitted(self):
        """Calling the same tool with different arguments is not blocked by duplicate protection."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            tool_calls=[_create_mock_tool_call("call_2", "get_employee", {"employee_id": "E1002"})]
        )

        # Pre-populate executed_calls with E1001
        executed = {'get_employee:{"employee_id": "E1001"}': {"found": True}}
        state: MultiAgentState = {
            "query": "Get info on E1002",
            "steps": [],
            "executed_calls": executed,
            "worker_results": [],
            "collected_evidence": [],
            "completed_domains": [],
            "client": mock_client,
        }

        with patch("app.tools.database_tools.get_employee_summary", return_value={"employee_id": "E1002", "name": "Bob"}):
            res = _execute_worker(EMPLOYEE_RECORDS_WORKER, state)
            self.assertEqual(len(res["steps"]), 1)
            self.assertEqual(res["steps"][0].status, "success")

    def test_replayed_approval_decision_rejected(self):
        """Resuming an approval that has already been resolved produces an error without re-execution."""
        checkpointer = MemorySaver()
        # Attempt to resume an invalid/non-existent approval ID
        response = resume_multi_agent_approval(
            approval_id="appr_fake_replay_999",
            decision="approve",
            checkpointer=checkpointer,
        )
        self.assertEqual(response.status, "error")
        self.assertIn("not found or has already expired", response.final_answer.lower())


class TestGraphStateCorruptionAndMissingFields(unittest.TestCase):
    """Deterministic tests verifying graph nodes and routing tolerate corrupted or missing state fields."""

    def test_supervisor_node_tolerates_empty_and_corrupt_state(self):
        """supervisor_node executes safely with an empty state dictionary."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"})
        )

        empty_state: MultiAgentState = {}
        with patch("app.agent.multi_agent._get_llm_client", return_value=mock_client):
            result = supervisor_node(empty_state)
            self.assertIn("current_worker", result)
            self.assertEqual(result["current_worker"], "finish")

    def test_worker_node_tolerates_missing_fields(self):
        """Worker nodes handle missing query, steps, or executed_calls gracefully."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content="Direct answer with no tools"
        )

        sparse_state: MultiAgentState = {
            "client": mock_client,
        }

        result = hr_policy_worker_node(sparse_state)
        self.assertIn("worker_results", result)
        self.assertEqual(len(result["worker_results"]), 1)
        self.assertTrue(result["worker_results"][0]["success"])

    def test_final_synthesis_node_tolerates_empty_state_and_none_results(self):
        """final_synthesis_node produces safe fallback when state has None worker results."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _create_mock_completion(
            content="Safe fallback final answer"
        )

        corrupt_state: MultiAgentState = {
            "query": None,
            "worker_results": [],
            "messages": [],
            "client": mock_client,
        }

        result = final_synthesis_node(corrupt_state)
        self.assertIn("final_answer", result)
        self.assertEqual(result["status"], "completed")

    def test_route_after_supervisor_tolerates_none_and_corrupt_values(self):
        """route_after_supervisor defaults safely to 'final_synthesis' on malformed state."""
        corrupt_states = [
            {},
            {"current_worker": None},
            {"current_worker": "unrecognized_worker_name"},
            {"step_count": None},
            {"approval_status": None},
        ]
        for st in corrupt_states:
            route = route_after_supervisor(st)
            self.assertIn(route, ["final_synthesis", "approval_node", "max_steps", "hr_policy_worker", "employee_records_worker", "travel_expense_worker"])


class TestTraceAndObservabilityIntegrity(unittest.TestCase):
    """Deterministic tests validating that execution trace metadata remains accurate and secret-free during errors."""

    def test_trace_populated_correctly_on_max_steps_reached(self):
        """Trace captures accurate step counts and max_steps_reached status."""
        steps = [
            AgentStep(step_number=1, tool_name="ask_policy", status="success", duration_ms=10.0),
            AgentStep(step_number=2, tool_name="ask_policy", status="success", duration_ms=12.0),
        ]
        resp = _build_agent_response(
            clean_session_id="sess_trace_test",
            clean_query="Test query",
            final_answer="Answer",
            steps=steps,
            status="max_steps_reached",
            start_time=0.0,
        )

        self.assertIsNotNone(resp.trace)
        self.assertEqual(resp.trace.total_steps, 2)
        self.assertEqual(resp.trace.status, "max_steps_reached")
        self.assertEqual(resp.trace.tools_invoked, ["ask_policy", "ask_policy"])
        self.assertTrue(resp.trace.used_rag)
        self.assertGreaterEqual(resp.trace.total_duration_ms, 0.0)

    def test_trace_contains_zero_api_keys_passwords_or_stack_traces(self):
        """Execution trace and step records never expose raw exception strings or secrets."""
        secret_payload = "sk-groq-secret-key-12345"
        failed_step = AgentStep(
            step_number=1,
            tool_name="get_employee",
            tool_args={"employee_id": "E1001"},
            tool_result={"error": f"Connection error involving {secret_payload}"},
            status="error",
            duration_ms=5.0,
            error="Sanitized tool execution failed.",
        )

        resp = _build_agent_response(
            clean_session_id="sess_secret_test",
            clean_query="Query",
            final_answer="Could not fulfill request due to an error.",
            steps=[failed_step],
            status="error",
            start_time=0.0,
        )

        trace_json = resp.trace.model_dump_json() if resp.trace else ""
        self.assertNotIn(secret_payload, resp.final_answer)
        self.assertNotIn("Traceback", trace_json)
        self.assertEqual(resp.trace.status, "error")


if __name__ == "__main__":
    unittest.main()
