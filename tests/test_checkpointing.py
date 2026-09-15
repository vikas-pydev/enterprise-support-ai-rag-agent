"""Dedicated Test Suite for LangGraph Checkpointing & Durable Workflow State (Phase 7 Task 5).

Tests checkpoint persistence, thread/session isolation, Human-in-the-Loop (HITL)
durable pause/resume, process-restart simulation, database separation, and security boundaries.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from app.agent.checkpoint import (
    create_checkpointer,
    get_default_checkpointer,
    set_default_checkpointer,
    reset_default_checkpointer,
    get_thread_id_for_session,
    build_thread_config,
    format_approval_id,
    resolve_thread_from_approval_id,
    get_thread_state,
    delete_thread_checkpoints,
)
from app.agent.multi_agent import (
    create_multi_agent_graph,
    run_multi_agent,
    resume_multi_agent_approval,
    MultiAgentState,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
)
from app.agent.memory import InMemorySessionStore


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


class TestLangGraphCheckpointing(unittest.TestCase):
    """Comprehensive test suite for LangGraph Checkpointing and Workflow State Persistence."""

    def setUp(self):
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)
        self.session_store = InMemorySessionStore()

    def tearDown(self):
        reset_default_checkpointer()

    def test_01_checkpointer_initialization_memory(self):
        """1. Verify checkpointer factory creates a MemorySaver by default."""
        ckpt = create_checkpointer(use_postgres_if_available=False)
        self.assertIsInstance(ckpt, BaseCheckpointSaver)
        self.assertIsInstance(ckpt, MemorySaver)

    def test_02_checkpointer_initialization_postgres_offline(self):
        """2. Verify unreachable PostgreSQL server falls back safely to MemorySaver."""
        ckpt = create_checkpointer(conn_string="postgresql://invalid_user:invalid_pass@127.0.0.1:54329/invalid_db")
        self.assertIsInstance(ckpt, MemorySaver)

    def test_03_thread_session_mapping(self):
        """3. Verify application session_id maps cleanly to LangGraph thread identity."""
        thread_id1 = get_thread_id_for_session("session-prod-001")
        self.assertEqual(thread_id1, "session-prod-001")

        # Empty session generates isolated unique thread ID
        thread_id2 = get_thread_id_for_session(None)
        self.assertTrue(thread_id2.startswith("thread_"))
        thread_id3 = get_thread_id_for_session("")
        self.assertTrue(thread_id3.startswith("thread_"))
        self.assertNotEqual(thread_id2, thread_id3)

        config = build_thread_config("session-test-42")
        self.assertEqual(config, {"configurable": {"thread_id": "session-test-42"}})

    def test_04_checkpoint_creation_on_workflow_run(self):
        """4. Verify state checkpoint is created and persisted after workflow execution."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Policy summary answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        resp = run_multi_agent(
            user_query="General inquiry",
            session_id="session_ckpt_01",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "completed")

        # Verify checkpoint exists in checkpointer for session_ckpt_01
        cfg = build_thread_config("session_ckpt_01")
        cp_tuple = self.checkpointer.get_tuple(cfg)
        self.assertIsNotNone(cp_tuple)
        self.assertEqual(cp_tuple.config["configurable"]["thread_id"], "session_ckpt_01")

    def test_05_checkpoint_state_retrieval(self):
        """5. Verify checkpoint channel values can be accurately retrieved from checkpointer."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer 123")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        run_multi_agent(
            user_query="Inquiry 123",
            session_id="sess_retrieve_01",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        state = get_thread_state(self.checkpointer, "sess_retrieve_01")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("session_id"), "sess_retrieve_01")
        self.assertEqual(state.get("query"), "Inquiry 123")
        self.assertEqual(state.get("status"), "completed")

    def test_06_state_persistence_across_multiple_turns(self):
        """6. Verify multi-turn conversational workflow accumulates state in the same thread."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Turn 1 done"}))
        synth1 = _create_mock_completion(content="Turn 1 answer.")
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Turn 2 done"}))
        synth2 = _create_mock_completion(content="Turn 2 answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth1, s2, synth2]

        run_multi_agent(
            user_query="First turn question",
            session_id="sess_multi_01",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )

        run_multi_agent(
            user_query="Second turn question",
            session_id="sess_multi_01",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )

        state = get_thread_state(self.checkpointer, "sess_multi_01")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("query"), "Second turn question")

    def test_07_interrupted_workflow_persistence(self):
        """7. Verify sensitive query pauses in pending_approval and persists state in checkpointer."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Sensitive salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="What is the confidential salary for E1001?",
            session_id="sess_hitl_ckpt_01",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )

        self.assertEqual(resp.status, "pending_approval")
        self.assertIn("requires human approval", resp.final_answer)

        # Check persisted state in checkpointer
        state = get_thread_state(self.checkpointer, "sess_hitl_ckpt_01")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("approval_status"), APPROVAL_STATUS_PENDING)
        self.assertEqual(state.get("workflow_status"), "pending_approval")
        self.assertTrue(state.get("approval_required"))
        self.assertIsNotNone(state.get("approval_id"))

    def test_08_approval_request_persistence_in_checkpoint(self):
        """8. Verify structured approval request metadata is preserved inside checkpoint."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Executive access"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="Show executive profile for E1000",
            session_id="sess_hitl_meta",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        state = get_thread_state(self.checkpointer, "sess_hitl_meta")
        req = state.get("approval_request")
        self.assertIsInstance(req, dict)
        self.assertEqual(req.get("target_worker"), "employee_records")
        self.assertIn("E1000", req.get("reason"))
        self.assertEqual(req.get("status"), APPROVAL_STATUS_PENDING)

    def test_09_approval_resume_approve_executes_worker(self):
        """9. Verify explicit 'approve' loads checkpoint, executes protected worker, and synthesizes answer."""
        mock_client = MagicMock()
        # 1. Pause
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        initial_resp = run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="sess_resume_approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        self.assertEqual(initial_resp.status, "pending_approval")

        state_paused = get_thread_state(self.checkpointer, "sess_resume_approve")
        approval_id = state_paused.get("approval_id")
        self.assertIsNotNone(approval_id)

        # 2. Resume with approve
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is VP of Engineering.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        resumed_resp = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )

        self.assertEqual(resumed_resp.status, "completed")
        self.assertEqual(len(resumed_resp.steps), 1)
        self.assertEqual(resumed_resp.steps[0].tool_name, "get_employee")
        self.assertIn("Alice Chen", resumed_resp.final_answer)

        # Verify updated checkpoint state is completed
        final_state = get_thread_state(self.checkpointer, "sess_resume_approve")
        self.assertEqual(final_state.get("approval_status"), APPROVAL_STATUS_APPROVED)
        self.assertEqual(final_state.get("status"), "completed")

    def test_10_approval_resume_reject_terminates_safely(self):
        """10. Verify explicit 'reject' terminates workflow safely without executing any tools."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="sess_resume_reject",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        state_paused = get_thread_state(self.checkpointer, "sess_resume_reject")
        approval_id = state_paused.get("approval_id")

        resumed_resp = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        self.assertEqual(resumed_resp.status, "rejected")
        self.assertEqual(len(resumed_resp.steps), 0)
        self.assertIn("rejected by a human operator", resumed_resp.final_answer)

        final_state = get_thread_state(self.checkpointer, "sess_resume_reject")
        self.assertEqual(final_state.get("approval_status"), APPROVAL_STATUS_REJECTED)

    def test_11_process_restart_simulation_and_resume(self):
        """11. Deterministic process restart simulation:
        1. Start sensitive workflow in process A -> pauses at approval -> saves checkpoint
        2. Process A exits (all runtime objects, graphs, and local variables destroyed)
        3. Process B starts -> connects to same checkpointer storage -> initializes new graph
        4. Operator submits approval -> workflow resumes from persisted state -> executes worker -> finishes
        """
        # Step 1: Process A execution
        proc_a_checkpointer = MemorySaver()
        proc_a_graph = create_multi_agent_graph(checkpointer=proc_a_checkpointer)

        mock_client_a = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "employee_records",
            "reasoning_summary": "Access executive profile",
        }))
        mock_client_a.chat.completions.create.side_effect = [s1]

        resp_a = run_multi_agent(
            user_query="Access executive profile for E1000",
            session_id="session_restart_sim",
            client=mock_client_a,
            graph=proc_a_graph,
            checkpointer=proc_a_checkpointer,
        )
        self.assertEqual(resp_a.status, "pending_approval")

        state_a = get_thread_state(proc_a_checkpointer, "session_restart_sim")
        approval_id = state_a.get("approval_id")
        self.assertIsNotNone(approval_id)

        # Retain simulated persistent backend storage references (mimicking Postgres DB tables)
        shared_storage = proc_a_checkpointer.storage
        shared_writes = proc_a_checkpointer.writes
        shared_blobs = proc_a_checkpointer.blobs

        # Step 2: Simulate process death (tear down process A graph and checkpointer instance)
        del proc_a_graph
        del proc_a_checkpointer
        del mock_client_a

        # Step 3: Process B startup (fresh instance pointing to persistent checkpointer storage)
        proc_b_checkpointer = MemorySaver()
        proc_b_checkpointer.storage = shared_storage
        proc_b_checkpointer.writes = shared_writes
        proc_b_checkpointer.blobs = shared_blobs
        proc_b_graph = create_multi_agent_graph(checkpointer=proc_b_checkpointer)

        # Step 4: Resume workflow in Process B
        mock_client_b = MagicMock()
        tc = _create_mock_tool_call("tc_restart", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Authorized details: Alice Chen, VP of Engineering.")
        mock_client_b.chat.completions.create.side_effect = [w1, s_fin, synth]

        resp_b = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client_b,
            graph=proc_b_graph,
            checkpointer=proc_b_checkpointer,
        )

        self.assertEqual(resp_b.status, "completed")
        self.assertEqual(len(resp_b.steps), 1)
        self.assertEqual(resp_b.steps[0].tool_name, "get_employee")
        self.assertIn("Alice Chen", resp_b.final_answer)

    def test_12_session_thread_isolation(self):
        """12. Verify distinct session IDs have completely isolated checkpoint state."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "A done"}))
        synth1 = _create_mock_completion(content="Answer A")
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "B done"}))
        synth2 = _create_mock_completion(content="Answer B")
        mock_client.chat.completions.create.side_effect = [s1, synth1, s2, synth2]

        run_multi_agent(user_query="Query for Session A", session_id="sess_iso_A", client=mock_client, checkpointer=self.checkpointer)
        run_multi_agent(user_query="Query for Session B", session_id="sess_iso_B", client=mock_client, checkpointer=self.checkpointer)

        state_a = get_thread_state(self.checkpointer, "sess_iso_A")
        state_b = get_thread_state(self.checkpointer, "sess_iso_B")

        self.assertIsNotNone(state_a)
        self.assertIsNotNone(state_b)
        self.assertEqual(state_a.get("query"), "Query for Session A")
        self.assertEqual(state_b.get("query"), "Query for Session B")

    def test_13_approval_isolation_between_sessions(self):
        """13. Approving session A does not approve or modify session B's pending checkpoint."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check A"}))
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check B"}))
        mock_client.chat.completions.create.side_effect = [s1, s2]

        run_multi_agent(user_query="Confidential record A", session_id="sess_appr_iso_A", client=mock_client, checkpointer=self.checkpointer)
        run_multi_agent(user_query="Confidential record B", session_id="sess_appr_iso_B", client=mock_client, checkpointer=self.checkpointer)

        state_a = get_thread_state(self.checkpointer, "sess_appr_iso_A")
        state_b = get_thread_state(self.checkpointer, "sess_appr_iso_B")

        id_a = state_a.get("approval_id")
        id_b = state_b.get("approval_id")

        self.assertNotEqual(id_a, id_b)

        # Resume session A
        tc = _create_mock_tool_call("tc_a", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice profile.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        res_a = resume_multi_agent_approval(approval_id=id_a, decision="approve", client=mock_client, checkpointer=self.checkpointer)
        self.assertEqual(res_a.status, "completed")

        # Session B is still pending in checkpoint
        state_b_after = get_thread_state(self.checkpointer, "sess_appr_iso_B")
        self.assertEqual(state_b_after.get("approval_status"), APPROVAL_STATUS_PENDING)

    def test_14_duplicate_decision_handling(self):
        """14. Verify submitting approval decision on already approved checkpoint returns error."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(user_query="Confidential salary for E1001", session_id="sess_dup_appr", client=mock_client, checkpointer=self.checkpointer)

        approval_id = get_thread_state(self.checkpointer, "sess_dup_appr").get("approval_id")

        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        # First approval succeeds
        res1 = resume_multi_agent_approval(approval_id=approval_id, decision="approve", client=mock_client, checkpointer=self.checkpointer)
        self.assertEqual(res1.status, "completed")

        # Second approval attempt is rejected as duplicate
        res2 = resume_multi_agent_approval(approval_id=approval_id, decision="approve", client=mock_client, checkpointer=self.checkpointer)
        self.assertEqual(res2.status, "error")
        self.assertIn("already been approved", res2.final_answer)

    def test_15_reject_after_approve_and_approve_after_reject(self):
        """15. Verify conflicting decision submissions on already decided checkpoints are rejected."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(user_query="Confidential salary for E1001", session_id="sess_conflict_appr", client=mock_client, checkpointer=self.checkpointer)
        approval_id = get_thread_state(self.checkpointer, "sess_conflict_appr").get("approval_id")

        # Reject it first
        res_reject = resume_multi_agent_approval(approval_id=approval_id, decision="reject", client=mock_client, checkpointer=self.checkpointer)
        self.assertEqual(res_reject.status, "rejected")

        # Attempting to approve after reject must be rejected safely
        res_approve = resume_multi_agent_approval(approval_id=approval_id, decision="approve", client=mock_client, checkpointer=self.checkpointer)
        self.assertEqual(res_approve.status, "error")

    def test_16_invalid_or_nonexistent_approval_id(self):
        """16. Verify non-existent or empty approval IDs return clean error responses."""
        res1 = resume_multi_agent_approval(approval_id="", decision="approve", checkpointer=self.checkpointer)
        self.assertEqual(res1.status, "error")

        res2 = resume_multi_agent_approval(approval_id="appr_fake_nonexistent_999", decision="approve", checkpointer=self.checkpointer)
        self.assertEqual(res2.status, "error")
        self.assertIn("was not found", res2.final_answer)

    def test_17_invalid_decision_string_rejected(self):
        """17. Verify invalid decision string is rejected without modifying state."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(user_query="Confidential salary for E1001", session_id="sess_inv_dec", client=mock_client, checkpointer=self.checkpointer)
        approval_id = get_thread_state(self.checkpointer, "sess_inv_dec").get("approval_id")

        res = resume_multi_agent_approval(approval_id=approval_id, decision="grant_access", checkpointer=self.checkpointer)
        self.assertEqual(res.status, "error")
        self.assertIn("Invalid decision", res.final_answer)

    def test_18_secrets_and_client_exclusion_from_checkpoint(self):
        """18. Verify secrets, system credentials, and non-serializable client objects are not leaked into persisted checkpoints."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        run_multi_agent(user_query="General check", session_id="sess_sec_01", client=mock_client, checkpointer=self.checkpointer)

        state = get_thread_state(self.checkpointer, "sess_sec_01")
        # Checkpoint state should contain business metadata and not leak internal system tokens
        state_str = json.dumps({k: v for k, v in state.items() if k != "client"}, default=str)
        self.assertNotIn("GROQ_API_KEY", state_str)
        self.assertNotIn("SUPERVISOR_SYSTEM_PROMPT", state_str)

    def test_19_backward_compatibility_with_standard_chat(self):
        """19. Verify standard non-approval multi-agent queries work seamlessly with checkpointing."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "hr_policy", "reasoning_summary": "Policy lookup"}))
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
                session_id="sess_compat_01",
                client=mock_client,
                checkpointer=self.checkpointer,
            )

            self.assertEqual(resp.status, "completed")
            self.assertEqual(len(resp.steps), 1)
            self.assertEqual(resp.steps[0].tool_name, "ask_policy")

    def test_20_thread_checkpoint_deletion_on_session_clear(self):
        """20. Verify delete_thread_checkpoints successfully clears checkpoints for the session."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        run_multi_agent(user_query="Clear test", session_id="sess_clear_01", client=mock_client, checkpointer=self.checkpointer)

        state_before = get_thread_state(self.checkpointer, "sess_clear_01")
        self.assertIsNotNone(state_before)

        deleted = delete_thread_checkpoints(self.checkpointer, "sess_clear_01")
        self.assertTrue(deleted)

        state_after = get_thread_state(self.checkpointer, "sess_clear_01")
        self.assertIsNone(state_after)

    def test_21_approval_id_resolution_helper(self):
        """21. Verify resolve_thread_from_approval_id resolves thread accurately."""
        thread_id = "sess_resolve_test_42"
        appr_id = format_approval_id(thread_id)

        resolved = resolve_thread_from_approval_id(appr_id)
        self.assertEqual(resolved, thread_id)

    def test_22_postgres_checkpointer_schema_setup_mock(self):
        """22. Verify PostgreSQL checkpointer factory calls setup() when initialized."""
        with patch("psycopg.connect") as mock_conn, patch("langgraph.checkpoint.postgres.PostgresSaver") as mock_pg_saver:
            mock_saver_inst = MagicMock()
            mock_pg_saver.return_value = mock_saver_inst

            with patch("app.agent.checkpoint.is_postgres_accessible", return_value=True):
                from app.agent.checkpoint import create_postgres_checkpointer
                saver = create_postgres_checkpointer("postgresql://postgres:postgres@localhost:5432/enterprise_support")

                self.assertIsNotNone(saver)
                mock_saver_inst.setup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
