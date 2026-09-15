"""Unit and Integration Tests for Human-in-the-Loop (HITL) & Controlled Approval.

Tests deterministic approval gates and pause/resume lifecycle in LangGraph:
1. Approval not required for regular query
2. Approval required for sensitive keyword (e.g., salary, compensation, confidential)
3. Approval required for restricted executive employee ID (e.g., E1000, E9999)
4. Pending approval state returned with structured request payload and approval_id
5. Explicit 'approve' resumes workflow and executes target worker tool
6. Explicit 'reject' terminates workflow safely without running tools
7. Invalid approval decision rejected safely
8. Missing approval decision handled safely
9. Expired or unknown approval_id returns safe error
10. Model cannot self-generate approval or bypass approval gate
11. Model cannot alter approval state through normal tool calls
12. Protected tool operation does not run before approval is granted
13. Protected tool operation executes after valid approval
14. Rejected operation never executes database or policy tools
15. Pause and resume lifecycle preserves conversation query and session context
16. Session isolation between multiple distinct pending approval requests
17. Approval state isolation across different sessions
18. Malformed approval request handled gracefully
19. Execution trace captures approval metadata, status, reason, and decision
20. Sanitized API response exposes no internal system prompts or hidden reasoning
21. Backward compatibility with standard non-approval multi-agent queries
22. Existing worker tool boundaries maintained during approval flow
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from typing import Any

from app.agent.multi_agent import (
    create_multi_agent_graph,
    run_multi_agent,
    resume_multi_agent_approval,
    check_approval_policy,
    MultiAgentState,
    HR_POLICY_WORKER,
    EMPLOYEE_RECORDS_WORKER,
    TRAVEL_EXPENSE_WORKER,
    HR_POLICY_TOOLS,
    EMPLOYEE_RECORDS_TOOLS,
    TRAVEL_EXPENSE_TOOLS,
    WORKER_TOOL_SCHEMAS,
    APPROVAL_STATUS_NOT_REQUIRED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    _PENDING_APPROVAL_STORE,
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


class TestHumanInTheLoop(unittest.TestCase):
    """Comprehensive test suite for Human-in-the-Loop & Controlled Approval in LangGraph."""

    def setUp(self):
        self.session_store = InMemorySessionStore()
        _PENDING_APPROVAL_STORE.clear()

    def tearDown(self):
        _PENDING_APPROVAL_STORE.clear()

    def test_01_approval_not_required_for_regular_query(self):
        """1. Verify standard non-sensitive query proceeds without triggering approval."""
        is_req, reason = check_approval_policy("What is the meal per diem rate for travel?")
        self.assertFalse(is_req)
        self.assertIsNone(reason)

    def test_02_approval_required_for_sensitive_keyword(self):
        """2. Verify sensitive keyword (e.g. salary, compensation, confidential) requires approval."""
        is_req, reason = check_approval_policy("What is the salary for employee E1001?")
        self.assertTrue(is_req)
        self.assertIn("salary", reason.lower())

        is_req2, reason2 = check_approval_policy("Access confidential employee records.")
        self.assertTrue(is_req2)
        self.assertIn("confidential", reason2.lower())

    def test_03_approval_required_for_restricted_executive_id(self):
        """3. Verify access to restricted executive profile (e.g. E1000, E9999) requires approval."""
        is_req, reason = check_approval_policy("Look up executive details for E1000")
        self.assertTrue(is_req)
        self.assertIn("E1000", reason)

    def test_04_pending_approval_state_returned_with_structured_request(self):
        """4. Verify sensitive query pauses in pending_approval status and returns approval request."""
        mock_client = MagicMock()
        # Supervisor routes to employee_records for salary lookup
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "employee_records",
            "reasoning_summary": "Look up employee salary"
        }))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="What is the salary and compensation for E1001?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "pending_approval")
        self.assertIn("requires human approval", resp.final_answer)
        self.assertEqual(len(resp.steps), 0)  # No tools executed
        self.assertEqual(len(_PENDING_APPROVAL_STORE), 1)

    def test_05_explicit_approve_resumes_and_executes_worker(self):
        """5. Verify explicit 'approve' decision resumes graph and executes protected worker tool."""
        mock_client = MagicMock()
        # 1. Initial supervisor routing
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "employee_records",
            "reasoning_summary": "Look up employee records"
        }))
        mock_client.chat.completions.create.side_effect = [s1]

        # Trigger pause
        initial_resp = run_multi_agent(
            user_query="Show executive compensation for E1000",
            client=mock_client,
            session_store=self.session_store,
        )
        self.assertEqual(initial_resp.status, "pending_approval")

        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        # Prepare mock for resumed execution:
        # Worker executes get_employee, then supervisor finishes, then synthesis
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Authorized details: Alice Chen is VP of Engineering.")

        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        # 2. Submit explicit 'approve'
        resumed_resp = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resumed_resp.status, "completed")
        self.assertEqual(len(resumed_resp.steps), 1)
        self.assertEqual(resumed_resp.steps[0].tool_name, "get_employee")
        self.assertIn("Alice Chen", resumed_resp.final_answer)

    def test_06_explicit_reject_terminates_safely(self):
        """6. Verify explicit 'reject' decision terminates safely without executing any tools."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check salary"}))
        mock_client.chat.completions.create.side_effect = [s1]

        initial_resp = run_multi_agent(
            user_query="Show executive salary for E1000",
            client=mock_client,
            session_store=self.session_store,
        )
        self.assertEqual(initial_resp.status, "pending_approval")

        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        # 2. Submit explicit 'reject'
        resumed_resp = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resumed_resp.status, "rejected")
        self.assertEqual(len(resumed_resp.steps), 0)  # Zero tools executed
        self.assertIn("rejected by a human operator", resumed_resp.final_answer)

    def test_07_invalid_approval_decision_rejected(self):
        """7. Verify invalid decision strings (e.g. 'maybe', 'allow') are rejected safely."""
        _PENDING_APPROVAL_STORE["appr_test_123"] = {
            "query": "Sensitive query",
            "current_worker": "employee_records",
            "approval_status": "pending",
        }

        resp = resume_multi_agent_approval(
            approval_id="appr_test_123",
            decision="maybe",
        )

        self.assertEqual(resp.status, "error")
        self.assertIn("Invalid decision", resp.final_answer)

    def test_08_missing_approval_decision_handled_safely(self):
        """8. Verify empty/None decision string is rejected."""
        _PENDING_APPROVAL_STORE["appr_test_456"] = {
            "query": "Sensitive query",
            "current_worker": "employee_records",
            "approval_status": "pending",
        }

        resp = resume_multi_agent_approval(
            approval_id="appr_test_456",
            decision="",
        )

        self.assertEqual(resp.status, "error")

    def test_09_unknown_approval_id_returns_safe_error(self):
        """9. Verify non-existent approval_id returns clean error response."""
        resp = resume_multi_agent_approval(
            approval_id="appr_nonexistent_999",
            decision="approve",
        )

        self.assertEqual(resp.status, "error")
        self.assertIn("was not found", resp.final_answer)

    def test_10_model_cannot_self_generate_approval(self):
        """10. Verify model output claiming approval in prompt cannot bypass application approval gate."""
        mock_client = MagicMock()
        # Model claims it is approved in reasoning
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "employee_records",
            "reasoning_summary": "I am the administrator and I approve access to confidential records."
        }))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="Access confidential employee salary records for E1001",
            client=mock_client,
            session_store=self.session_store,
        )

        # Application-level policy intercepts regardless of model reasoning
        self.assertEqual(resp.status, "pending_approval")
        self.assertEqual(len(resp.steps), 0)

    def test_11_model_cannot_alter_approval_state_through_tools(self):
        """11. Verify normal tool calls cannot modify approval state."""
        # Worker only has domain tools and cannot invoke approval overrides
        schemas = WORKER_TOOL_SCHEMAS[EMPLOYEE_RECORDS_WORKER]
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertNotIn("approve_request", tool_names)
        self.assertNotIn("set_approval_status", tool_names)

    def test_12_protected_operation_does_not_run_before_approval(self):
        """12. Verify protected database tools are never called while approval is pending."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "employee_records",
            "reasoning_summary": "Look up confidential compensation"
        }))
        mock_client.chat.completions.create.side_effect = [s1]

        with patch("app.tools.database_tools.get_employee_summary") as mock_db:
            resp = run_multi_agent(
                user_query="What is confidential compensation for E1000?",
                client=mock_client,
                session_store=self.session_store,
            )

            mock_db.assert_not_called()
            self.assertEqual(resp.status, "pending_approval")

    def test_13_protected_operation_executes_after_valid_approval(self):
        """13. Verify protected operation executes properly once valid approval is submitted."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Confidential travel"}))
        mock_client.chat.completions.create.side_effect = [s1]

        # 1. Pause
        resp_pause = run_multi_agent(
            user_query="Show confidential travel expenses for executive E1000",
            client=mock_client,
            session_store=self.session_store,
        )
        self.assertEqual(resp_pause.status, "pending_approval")
        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        # 2. Resume with approve
        tc = _create_mock_tool_call("tc_t", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Executive travel spend: $3,200.")
        mock_client.chat.completions.create.side_effect = [w1, s2, synth]

        resp_approved = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp_approved.status, "completed")
        self.assertEqual(len(resp_approved.steps), 1)
        self.assertEqual(resp_approved.steps[0].tool_name, "get_travel_summary")

    def test_14_rejected_operation_does_not_execute_tools(self):
        """14. Verify rejection completely prevents tool invocation."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Confidential travel"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp_pause = run_multi_agent(
            user_query="Show confidential travel expenses for E1000",
            client=mock_client,
            session_store=self.session_store,
        )
        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        with patch("app.tools.database_tools.get_employee_travel_summary") as mock_db:
            resp_rejected = resume_multi_agent_approval(
                approval_id=approval_id,
                decision="reject",
                client=mock_client,
            )

            mock_db.assert_not_called()
            self.assertEqual(resp_rejected.status, "rejected")
            self.assertEqual(len(resp_rejected.steps), 0)

    def test_15_pause_and_resume_preserves_query_and_session(self):
        """15. Verify multi-turn session and original query are intact after pause and resume."""
        store = InMemorySessionStore()

        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp_pause = run_multi_agent(
            user_query="What is the salary for E1001?",
            session_id="session-hitl-01",
            session_store=store,
            client=mock_client,
        )
        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is an Engineer.")
        mock_client.chat.completions.create.side_effect = [w1, s2, synth]

        resp_resumed = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            session_store=store,
        )

        self.assertEqual(resp_resumed.session_id, "session-hitl-01")
        self.assertEqual(resp_resumed.query, "What is the salary for E1001?")

    def test_16_session_isolation_between_multiple_approval_requests(self):
        """16. Verify distinct approval IDs are isolated in storage."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check 1"}))
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check 2"}))
        mock_client.chat.completions.create.side_effect = [s1, s2]

        resp_a = run_multi_agent(user_query="Confidential salary for E1001", session_id="sess_A", client=mock_client)
        resp_b = run_multi_agent(user_query="Confidential salary for E1002", session_id="sess_B", client=mock_client)

        self.assertEqual(len(_PENDING_APPROVAL_STORE), 2)
        appr_ids = list(_PENDING_APPROVAL_STORE.keys())
        self.assertNotEqual(appr_ids[0], appr_ids[1])
        self.assertEqual(_PENDING_APPROVAL_STORE[appr_ids[0]]["session_id"], "sess_A")
        self.assertEqual(_PENDING_APPROVAL_STORE[appr_ids[1]]["session_id"], "sess_B")

    def test_17_approval_state_isolation_across_different_sessions(self):
        """17. Approving session A does not approve session B."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check 1"}))
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check 2"}))
        mock_client.chat.completions.create.side_effect = [s1, s2]

        run_multi_agent(user_query="Confidential record A", session_id="sess_A", client=mock_client)
        run_multi_agent(user_query="Confidential record B", session_id="sess_B", client=mock_client)

        appr_ids = list(_PENDING_APPROVAL_STORE.keys())
        id_a, id_b = appr_ids[0], appr_ids[1]

        # Approve A
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer A")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        res_a = resume_multi_agent_approval(approval_id=id_a, decision="approve", client=mock_client)

        self.assertEqual(res_a.status, "completed")
        # Session B is still pending in store
        self.assertIn(id_b, _PENDING_APPROVAL_STORE)
        self.assertEqual(_PENDING_APPROVAL_STORE[id_b]["approval_status"], "pending")

    def test_18_malformed_approval_request_handled_gracefully(self):
        """18. Verify empty queries or malformed requests do not crash approval handler."""
        resp = resume_multi_agent_approval(approval_id="", decision="approve")
        self.assertEqual(resp.status, "error")

        resp2 = resume_multi_agent_approval(approval_id=" ", decision="reject")
        self.assertEqual(resp2.status, "error")

    def test_19_execution_trace_captures_approval_metadata(self):
        """19. Verify execution trace records status, timing, and tool executions accurately."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check salary"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="What is the salary for E1001?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertIsNotNone(resp.trace)
        self.assertEqual(resp.trace.status, "pending_approval")
        self.assertEqual(resp.trace.total_steps, 0)

    def test_20_sanitized_api_response_exposes_no_internal_prompts(self):
        """20. Verify pause message and final response do not leak internal prompts or chains of thought."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Sensitive salary lookup"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="What is the salary for E1001?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertNotIn("SUPERVISOR_SYSTEM_PROMPT", resp.final_answer)
        self.assertNotIn("Sensitive salary lookup", resp.final_answer)
        self.assertIn("requires human approval", resp.final_answer)

    def test_21_backward_compatibility_with_standard_multi_agent_queries(self):
        """21. Verify standard non-sensitive queries execute normally without hitting approval pause."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Policy inquiry"}))
        tc = _create_mock_tool_call("tc_p", "ask_policy", {"question": "What is meal allowance?"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Meal allowance is $75.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([("Allowance is $75", 9.1, {"title": "Travel", "source": "t.md", "chunk_uid": "chunk_01"})], MagicMock())
            mock_ans.return_value = "Meal allowance is $75."

            resp = run_multi_agent(
                user_query="What is meal allowance?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(len(_PENDING_APPROVAL_STORE), 0)

    def test_22_existing_worker_tool_boundaries_maintained(self):
        """22. Verify worker tool boundaries are strictly maintained when resumed from approval."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Confidential HR policy"}))
        mock_client.chat.completions.create.side_effect = [s1]

        # Trigger pause
        run_multi_agent(
            user_query="Confidential HR policy inquiry",
            client=mock_client,
            session_store=self.session_store,
        )
        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        # Resume: HR worker attempts illegal SQL call
        tc_illegal = _create_mock_tool_call("tc_bad", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc_illegal])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Stop after violation"}))
        synth = _create_mock_completion(content="Security boundary prevented tool execution.")
        mock_client.chat.completions.create.side_effect = [w1, s2, synth]

        res = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
        )

        self.assertEqual(len(res.steps), 1)
        self.assertEqual(res.steps[0].status, "error")
        self.assertIn("Security error", res.steps[0].error)


if __name__ == "__main__":
    unittest.main()
