"""Unit and Integration Tests for Multi-Step Workflows & Conditional Branching.

Tests advanced LangGraph multi-agent orchestration:
1. Single-domain completion (HR Policy)
2. Single-domain completion (Employee Records)
3. Single-domain completion (Travel & Expense)
4. Two-domain workflow (Travel & Expense + HR Policy: Travel Spend + Meal Allowance)
5. Two-domain workflow (Travel & Expense + Employee Records: Spend + Manager)
6. Intra-domain multi-step workflow (Employee Records: Profile + Leave Balance)
7. Conditional worker selection based on prior worker observations
8. Evidence-dependent routing (stops routing when all evidence collected)
9. Unnecessary-worker prevention (does not invoke third domain if inquiry is satisfied)
10. Repeated-worker protection (detects worker with no progress and breaks loop)
11. Worker-cycle protection (detects A -> B -> A -> B cycling)
12. Duplicate-call protection across workflow turns
13. Clarification routing when employee ID is missing (e.g. "What is my leave balance?")
14. Missing employee identifier in travel inquiry triggers clarification
15. Max workflow/tool steps enforcement
16. Final synthesis uses only collected worker evidence
17. Citation preservation through multi-step flows
18. Worker tool isolation (worker cannot invoke tools outside its domain)
19. Multi-turn session context carries over to multi-step workflow
20. Backward compatibility with existing single-turn run_multi_agent() invocations
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


class TestMultiAgentWorkflows(unittest.TestCase):
    """Test suite for Multi-Step Workflows, Conditional Branching, Clarification, and Stall Protection."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            p.stop()

    def setUp(self):
        self.session_store = InMemorySessionStore()

    def test_01_single_domain_completion_hr_policy(self):
        """1. Single-domain completion for HR policy inquiry."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "hr_policy",
            "reasoning_summary": "Policy question on remote work",
            "completed_domains": [],
            "missing_information": []
        }))
        tc = _create_mock_tool_call("tc_p1", "ask_policy", {"question": "What is the remote work policy?"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({
            "next_worker": "finish",
            "reasoning_summary": "Remote work policy retrieved",
            "completed_domains": ["hr_policy"],
            "missing_information": []
        }))
        synth = _create_mock_completion(content="Remote work is permitted up to 2 days per week [Remote_Policy.md].")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([("Remote policy: 2 days/week", 9.0, {"title": "Remote", "source": "Remote_Policy.md", "chunk_uid": "chunk_rw_1"})], MagicMock())
            mock_ans.return_value = "Remote work is permitted up to 2 days per week."

            resp = run_multi_agent(
                user_query="What is the remote work policy?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertTrue(resp.used_rag)
            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(resp.steps[0].tool_name, "ask_policy")
            self.assertIn("Remote work", resp.final_answer)

    def test_02_single_domain_completion_employee_records(self):
        """2. Single-domain completion for employee records inquiry."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup employee"}))
        tc = _create_mock_tool_call("tc_e1", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Employee found"}))
        synth = _create_mock_completion(content="Alice Chen is in Engineering.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="What department does E1001 belong to?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertFalse(resp.used_rag)
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_employee")

    def test_03_single_domain_completion_travel_expense(self):
        """3. Single-domain completion for travel expense inquiry."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Lookup expenses"}))
        tc = _create_mock_tool_call("tc_t1", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Expenses found"}))
        synth = _create_mock_completion(content="E1001 has spent $3,200 on travel.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="How much has E1001 spent on travel?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")

    def test_04_two_domain_workflow_travel_and_policy(self):
        """4. Two-domain workflow: Travel & Expense + HR Policy (Travel Spend + Meal Allowance)."""
        mock_client = MagicMock()
        # 1. Supervisor routes to travel_expense
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "travel_expense",
            "reasoning_summary": "First check travel expense for E1001",
            "missing_information": ["policy meal allowance"],
            "completed_domains": []
        }))
        tc1 = _create_mock_tool_call("tc_t1", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        # 2. Supervisor routes to hr_policy
        s2 = _create_mock_completion(content=json.dumps({
            "next_worker": "hr_policy",
            "reasoning_summary": "Now check travel meal allowance policy",
            "missing_information": [],
            "completed_domains": ["travel_expense"]
        }))
        tc2 = _create_mock_tool_call("tc_p1", "ask_policy", {"question": "What is the travel meal allowance per diem?"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        # 3. Supervisor finishes
        s3 = _create_mock_completion(content=json.dumps({
            "next_worker": "finish",
            "reasoning_summary": "Both travel spend and meal allowance policy collected",
            "completed_domains": ["travel_expense", "hr_policy"],
            "missing_information": []
        }))
        synth = _create_mock_completion(content="E1001 has spent $3,200 on travel, and the daily meal allowance policy is $75/day [Travel_Policy.md].")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, s3, synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = ([("Per diem is $75", 9.2, {"title": "Travel Policy", "source": "Travel_Policy.md", "chunk_uid": "chunk_tp_01"})], MagicMock())
            mock_ans.return_value = "Daily meal allowance is $75."

            resp = run_multi_agent(
                user_query="How much did E1001 spend on travel and what is the travel meal allowance?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertEqual(resp.status, "completed")
            self.assertTrue(resp.used_rag)
            self.assertEqual(len(resp.steps), 2)
            self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")
            self.assertEqual(resp.steps[1].tool_name, "ask_policy")
            self.assertIn("$3,200", resp.final_answer)
            self.assertIn("$75", resp.final_answer)
            self.assertEqual(len(resp.citations), 1)

    def test_05_two_domain_workflow_travel_and_employee(self):
        """5. Two-domain workflow: Travel & Expense + Employee Records (Spend + Manager Name)."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Fetch travel expenses"}))
        tc1 = _create_mock_tool_call("tc_trav", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Fetch employee profile for manager"}))
        tc2 = _create_mock_tool_call("tc_emp", "get_employee", {"employee_id": "E1001"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "All data collected"}))
        synth = _create_mock_completion(content="Alice Chen has spent $3,200 on travel, and her direct manager is Bob Smith.")

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

    def test_06_intra_domain_multistep_workflow(self):
        """6. Intra-domain multi-step workflow (Employee Records: Profile + Leave Balance)."""
        mock_client = MagicMock()
        # 1. Supervisor routes to employee_records for manager
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check employee manager"}))
        tc1 = _create_mock_tool_call("tc_e1", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        # 2. Supervisor routes again to employee_records for leave balance
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check employee leave balance"}))
        tc2 = _create_mock_tool_call("tc_l1", "get_leave_balance", {"employee_id": "E1001"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        # 3. Supervisor finishes
        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Manager and leave balance both collected"}))
        synth = _create_mock_completion(content="Alice Chen's manager is Bob Smith and she has 14 days of annual leave remaining.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, s3, synth]

        resp = run_multi_agent(
            user_query="Tell me E1001's manager and how much annual leave they have remaining.",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].tool_name, "get_employee")
        self.assertEqual(resp.steps[1].tool_name, "get_leave_balance")
        self.assertIn("Bob Smith", resp.final_answer)
        self.assertIn("14 days", resp.final_answer)

    def test_07_conditional_worker_selection_based_on_observations(self):
        """7. Conditional worker selection switches route dynamically after receiving first observation."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check department"}))
        tc1 = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        # Based on employee department being Engineering, supervisor decides to check department roster
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Now list Engineering department employees"}))
        tc2 = _create_mock_tool_call("tc_dept", "list_department_employees", {"department": "Engineering"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Completed"}))
        synth = _create_mock_completion(content="E1001 is in Engineering, which includes Alice Chen and Bob Smith.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, s3, synth]

        resp = run_multi_agent(
            user_query="What department is E1001 in, and who else works there?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].tool_name, "get_employee")
        self.assertEqual(resp.steps[1].tool_name, "list_department_employees")

    def test_08_evidence_dependent_routing_stops_when_satisfied(self):
        """8. Evidence-dependent routing stops calling workers once all required evidence is collected."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Look up expenses"}))
        tc = _create_mock_tool_call("tc_t", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])

        # Supervisor sees full travel summary returned and stops
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "All required expense data collected"}))
        synth = _create_mock_completion(content="Total spend is $3,200.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="How much has E1001 spent on flights and hotels?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].tool_name, "get_travel_summary")

    def test_09_unnecessary_worker_prevention(self):
        """9. Unnecessary-worker prevention: Does not route to policy agent when only operational data is needed."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup leave balance"}))
        tc = _create_mock_tool_call("tc_l", "get_leave_balance", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Leave balance obtained"}))
        synth = _create_mock_completion(content="14 days remaining.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="How many PTO days does E1001 have left?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertFalse(resp.used_rag)
        self.assertEqual(len(resp.steps), 1)

    def test_10_repeated_worker_protection_detects_stall(self):
        """10. Repeated-worker protection: Detects worker with no progress/repeated calls and terminates safely."""
        mock_client = MagicMock()
        # Supervisor repeatedly calls employee_records, but worker returns direct text without new tools
        s_call = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Try again"}))
        w_direct = _create_mock_completion(content="No additional info found.")
        synth = _create_mock_completion(content="Could not find further information.")

        mock_client.chat.completions.create.side_effect = [
            s_call, w_direct,
            s_call, w_direct,
            s_call,  # Third supervisor call triggers stall protection -> finish
            synth,
        ]

        resp = run_multi_agent(
            user_query="Keep trying employee records",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")

    def test_11_worker_cycle_protection(self):
        """11. Worker-cycle protection: Detects A -> B -> A -> B cycling and terminates safely."""
        mock_client = MagicMock()
        s_hr = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Policy check"}))
        w_hr = _create_mock_completion(content="No policy info.")
        s_emp = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Employee check"}))
        w_emp = _create_mock_completion(content="No employee info.")
        synth = _create_mock_completion(content="Terminated cycle safely.")

        mock_client.chat.completions.create.side_effect = [
            s_hr, w_hr,
            s_emp, w_emp,
            s_hr, w_hr,
            s_emp, w_emp,
            s_hr,  # Triggers cycle detection -> finish
            synth,
        ]

        resp = run_multi_agent(
            user_query="Cycle test between policy and employee",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")

    def test_12_duplicate_call_protection_across_turns(self):
        """12. In-run duplicate call protection caches observation and rejects redundant tool executions."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Step 1"}))
        tc1 = _create_mock_tool_call("tc_1", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Step 2"}))
        tc2 = _create_mock_tool_call("tc_2", "get_employee", {"employee_id": "E1001"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is in Engineering.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, s3, synth]

        resp = run_multi_agent(
            user_query="Lookup E1001 twice",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(len(resp.steps), 2)
        self.assertEqual(resp.steps[0].status, "success")
        self.assertEqual(resp.steps[1].status, "rejected_duplicate")

    def test_13_clarification_routing_when_employee_id_missing(self):
        """13. Clarification routing: When essential employee ID is missing, routes to clarify."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "clarify",
            "reasoning_summary": "User asked for leave balance without providing employee ID",
            "missing_information": ["employee_id"],
            "completed_domains": []
        }))
        clarify_synth = _create_mock_completion(content="Please provide your Employee ID (e.g., E1001) so I can look up your leave balance.")

        mock_client.chat.completions.create.side_effect = [s1, clarify_synth]

        resp = run_multi_agent(
            user_query="What is my leave balance?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")
        self.assertEqual(len(resp.steps), 0)
        self.assertIn("Employee ID", resp.final_answer)

    def test_14_missing_employee_identifier_in_travel_triggers_clarification(self):
        """14. Missing employee identifier in travel expense query triggers clarification."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "clarify",
            "reasoning_summary": "Missing employee ID for travel summary inquiry",
            "missing_information": ["employee_id"]
        }))
        clarify_synth = _create_mock_completion(content="Could you please specify the Employee ID for the travel expense lookup?")

        mock_client.chat.completions.create.side_effect = [s1, clarify_synth]

        resp = run_multi_agent(
            user_query="How much did they spend on travel?",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(len(resp.steps), 0)
        self.assertIn("Employee ID", resp.final_answer)

    def test_15_max_workflow_tool_steps_enforcement(self):
        """15. Hard step budget limit enforces max_steps termination safely."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Step 1"}))
        tc1 = _create_mock_tool_call("tc_1", "get_travel_summary", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        s2 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Step 2"}))
        tc2 = _create_mock_tool_call("tc_2", "get_travel_summary", {"employee_id": "E1002"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        max_steps_synth = _create_mock_completion(content="Maximum step limit reached.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, max_steps_synth]

        resp = run_multi_agent(
            user_query="Loop expenses with budget 2",
            max_steps=2,
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "max_steps_reached")
        self.assertEqual(len(resp.steps), 2)

    def test_16_final_synthesis_uses_only_collected_evidence(self):
        """16. Final synthesis prompt provides only gathered worker observations to LLM."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Get profile"}))
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is an Engineer.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="Lookup E1001",
            client=mock_client,
            session_store=self.session_store,
        )

        # Inspect messages passed to final synthesis (last call to client)
        synth_messages = mock_client.chat.completions.create.call_args_list[-1][1]["messages"]
        user_prompt_content = synth_messages[-1]["content"]
        self.assertIn("GATHERED EVIDENCE", user_prompt_content)
        self.assertIn("Alice Chen", user_prompt_content)

    def test_17_citation_preservation_through_multistep_flow(self):
        """17. Citations from RAG policy tools survive multi-step multi-worker workflows."""
        mock_client = MagicMock()
        # Step 1: Employee
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check employee"}))
        tc1 = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])

        # Step 2: Policy
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Check per diem policy"}))
        tc2 = _create_mock_tool_call("tc_p", "ask_policy", {"question": "What is meal per diem?"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])

        # Step 3: Finish
        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen can claim $75 meal per diem [Travel_Policy.md].")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, w2, s3, synth]

        with patch("app.tools.rag_tools.retrieve") as mock_ret, patch("app.tools.rag_tools.generate_answer") as mock_ans:
            mock_ret.return_value = (
                [("Per diem is $75", 9.5, {"title": "Travel Policy", "source": "Travel_Policy.md", "chunk_uid": "chunk_multi_01"})],
                MagicMock(),
            )
            mock_ans.return_value = "Per diem is $75."

            resp = run_multi_agent(
                user_query="Can employee E1001 claim meal per diem and what is the rate?",
                client=mock_client,
                session_store=self.session_store,
            )

            self.assertTrue(resp.used_rag)
            self.assertEqual(len(resp.citations), 1)
            self.assertEqual(resp.citations[0]["chunk_uid"], "chunk_multi_01")
            self.assertEqual(resp.citations[0]["title"], "Travel Policy")

    def test_18_worker_tool_isolation_enforced(self):
        """18. Strict boundary enforcement: Travel worker cannot execute policy tools."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Route to travel worker"}))
        # Travel worker attempts unauthorized policy call
        tc_bad = _create_mock_tool_call("tc_bad", "ask_policy", {"question": "What is leave policy?"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc_bad])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Stop after error"}))
        synth = _create_mock_completion(content="Security boundary prevented unauthorized tool invocation.")

        mock_client.chat.completions.create.side_effect = [s1, w1, s2, synth]

        resp = run_multi_agent(
            user_query="Have travel worker query policy",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertEqual(len(resp.steps), 1)
        self.assertEqual(resp.steps[0].status, "error")
        self.assertIn("Security error: Worker 'travel_expense' is not authorized", resp.steps[0].error)

    def test_19_multiturn_session_context_carries_over(self):
        """19. Conversation history resolves pronouns across multiple turns."""
        store = InMemorySessionStore()

        # Turn 1: Ask about E1001
        mock_client1 = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup E1001"}))
        tc1 = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc1])
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Profile found"}))
        synth1 = _create_mock_completion(content="E1001 is Alice Chen.")
        mock_client1.chat.completions.create.side_effect = [s1, w1, s2, synth1]

        resp1 = run_multi_agent(
            user_query="Who is E1001?",
            session_id="multi-turn-01",
            session_store=store,
            client=mock_client1,
        )

        # Turn 2: Follow-up asking "How much have they spent on travel?"
        mock_client2 = MagicMock()
        s3 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Lookup travel for Alice Chen (E1001)"}))
        tc2 = _create_mock_tool_call("tc_t", "get_travel_summary", {"employee_id": "E1001"})
        w2 = _create_mock_completion(content=None, tool_calls=[tc2])
        s4 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Travel found"}))
        synth2 = _create_mock_completion(content="Alice Chen has spent $3,200 on travel.")
        mock_client2.chat.completions.create.side_effect = [s3, w2, s4, synth2]

        resp2 = run_multi_agent(
            user_query="How much have they spent on travel?",
            session_id="multi-turn-01",
            session_store=store,
            client=mock_client2,
        )

        self.assertEqual(resp2.status, "completed")
        self.assertEqual(len(resp2.steps), 1)
        self.assertEqual(resp2.steps[0].tool_name, "get_travel_summary")
        self.assertEqual(resp2.steps[0].tool_args, {"employee_id": "E1001"})

    def test_20_backward_compatibility_with_existing_runner(self):
        """20. run_multi_agent returns standardized AgentResponse with trace, timing, and citations."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Direct reply"}))
        synth = _create_mock_completion(content="Enterprise Support Multi-Agent ready.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        resp = run_multi_agent(
            user_query="Hello!",
            client=mock_client,
            session_store=self.session_store,
        )

        self.assertIsInstance(resp, AgentResponse)
        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.trace)
        self.assertEqual(resp.trace.status, "completed")
        self.assertEqual(resp.final_answer, "Enterprise Support Multi-Agent ready.")


if __name__ == "__main__":
    unittest.main()
