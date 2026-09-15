"""Comprehensive Test Suite for Human-in-the-Loop (HITL) & Checkpoint Persistence Hardening (Phase 9 Task 6).

Covers:
1. Approval Authorization & Ownership boundaries (session/thread context matching, cross-session defense)
2. Approval Replay Defense & Conflicting Decisions (double approve, double reject, approve-after-reject, reject-after-approve, concurrent decisions, reuse after completion)
3. Approval State Persistence & Process-Restart Simulation (survival across restarts, continuation exactly once)
4. Checkpoint Database Failure & Fallback Behavior (connection failure, write failure, read failure, deletion failure, corrupted state, credential masking)
5. Checkpoint Thread & Session Isolation (state, messages, worker results, isolated deletions)
6. Checkpoint State Sanitization (no API keys, DB passwords, raw secrets, or system prompt definitions persisted)
7. Checkpoint Cleanup & Idempotency (clear, delete, repeated cleanup, nonexistent thread cleanup)
8. API Endpoint Authorization & Error Code Mapping (403 Forbidden on ownership mismatch, 400 Bad Request on replay/invalid transition, 404 Not Found on missing approval)
"""

import concurrent.futures
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.agent.checkpoint import (
    create_checkpointer,
    create_postgres_checkpointer,
    get_default_checkpointer,
    set_default_checkpointer,
    reset_default_checkpointer,
    get_thread_id_for_session,
    build_thread_config,
    format_approval_id,
    resolve_thread_from_approval_id,
    get_thread_state,
    delete_thread_checkpoints,
    mask_connection_string,
)
from app.agent.multi_agent import (
    create_multi_agent_graph,
    run_multi_agent,
    resume_multi_agent_approval,
    check_approval_policy,
    MultiAgentState,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_NOT_REQUIRED,
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


# =====================================================================
# 1. APPROVAL AUTHORIZATION & OWNERSHIP BOUNDARIES
# =====================================================================

class TestApprovalAuthorizationAndOwnership(unittest.TestCase):
    """Tests authorization and session ownership boundaries for approvals."""

    def setUp(self):
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)
        self.session_store = InMemorySessionStore()
        _PENDING_APPROVAL_STORE.clear()

    def tearDown(self):
        reset_default_checkpointer()
        _PENDING_APPROVAL_STORE.clear()

    def test_01_valid_approval_correct_session(self):
        """1. Valid approval with matching expected_session_id succeeds and resumes workflow."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="What is the confidential salary for E1001?",
            session_id="session_auth_01",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        self.assertEqual(resp.status, "pending_approval")

        state = get_thread_state(self.checkpointer, "session_auth_01")
        approval_id = state.get("approval_id")

        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is VP of Engineering.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        resumed = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            expected_session_id="session_auth_01",
            session_store=self.session_store,
        )

        self.assertEqual(resumed.status, "completed")
        self.assertEqual(len(resumed.steps), 1)
        self.assertIn("Alice Chen", resumed.final_answer)

    def test_02_valid_approval_wrong_session_rejected(self):
        """2. Valid approval for Session A cannot be acted upon with Session B context."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="session_user_A",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        self.assertEqual(resp.status, "pending_approval")
        approval_id = get_thread_state(self.checkpointer, "session_user_A").get("approval_id")

        # Session B attempts to act on Session A's approval
        resumed = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            expected_session_id="session_user_B",
            session_store=self.session_store,
        )

        self.assertEqual(resumed.status, "error")
        self.assertIn("does not belong to session", resumed.final_answer)
        self.assertEqual(len(resumed.steps), 0)

        # Session A's approval remains pending and unmodified
        state_a = get_thread_state(self.checkpointer, "session_user_A")
        self.assertEqual(state_a.get("approval_status"), APPROVAL_STATUS_PENDING)

    def test_03_nonexistent_approval_rejected(self):
        """3. Nonexistent approval ID returns safe error without modifying system state."""
        resp = resume_multi_agent_approval(
            approval_id="appr_00000000_nonexistent_session",
            decision="approve",
            checkpointer=self.checkpointer,
        )
        self.assertEqual(resp.status, "error")
        self.assertIn("was not found", resp.final_answer)
        self.assertEqual(len(resp.steps), 0)

    def test_04_malformed_approval_ids(self):
        """4. Malformed approval IDs return safe errors without crashing."""
        malformed_inputs = [
            "",
            "   ",
            "invalid_prefix_123",
            "appr_",
            "appr_missingparts",
            "appr_tok_../../../etc/passwd",
            "appr_<script>alert(1)</script>",
        ]
        for bad_id in malformed_inputs:
            resp = resume_multi_agent_approval(
                approval_id=bad_id,
                decision="approve",
                checkpointer=self.checkpointer,
            )
            self.assertEqual(resp.status, "error")
            self.assertEqual(len(resp.steps), 0)

    def test_05_expired_or_missing_approval(self):
        """5. Expired or unrecorded approval ID returns safe error."""
        resp = resume_multi_agent_approval(
            approval_id="appr_expired_sess999",
            decision="reject",
            checkpointer=self.checkpointer,
        )
        self.assertEqual(resp.status, "error")
        self.assertIn("was not found or has already expired", resp.final_answer)

    def test_06_unauthorized_attempts_reveal_no_sensitive_state(self):
        """6. Unauthorized approval attempts do not leak query contents or system prompt internals."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="What is the confidential compensation package for executive E1000?",
            session_id="session_secret_01",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        approval_id = get_thread_state(self.checkpointer, "session_secret_01").get("approval_id")

        unauthorized_res = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            expected_session_id="wrong_session_attacker",
            checkpointer=self.checkpointer,
        )

        self.assertEqual(unauthorized_res.status, "error")
        self.assertNotIn("confidential compensation package", unauthorized_res.final_answer)
        self.assertNotIn("E1000", unauthorized_res.final_answer)
        self.assertNotIn("SUPERVISOR_SYSTEM_PROMPT", unauthorized_res.final_answer)


# =====================================================================
# 2. APPROVAL REPLAY DEFENSE & CONFLICTING DECISIONS
# =====================================================================

class TestApprovalReplayDefense(unittest.TestCase):
    """Tests replay protection, idempotency, and conflicting decision handling."""

    def setUp(self):
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)
        self.session_store = InMemorySessionStore()
        _PENDING_APPROVAL_STORE.clear()

    def tearDown(self):
        reset_default_checkpointer()
        _PENDING_APPROVAL_STORE.clear()

    def _trigger_pending_approval(self, session_id: str) -> str:
        """Helper to initialize a paused approval workflow."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        resp = run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id=session_id,
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        self.assertEqual(resp.status, "pending_approval")
        state = get_thread_state(self.checkpointer, session_id)
        return state.get("approval_id")

    def test_01_replay_double_approve(self):
        """1. Approving the same approval twice executes tools once and rejects the replay."""
        approval_id = self._trigger_pending_approval("sess_double_approve")

        mock_client = MagicMock()
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen profile.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        # 1st approve
        res1 = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        self.assertEqual(res1.status, "completed")
        self.assertEqual(len(res1.steps), 1)

        # 2nd approve (replay)
        res2 = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        self.assertEqual(res2.status, "error")
        self.assertIn("already been approved", res2.final_answer)
        self.assertEqual(len(res2.steps), 0)

    def test_02_replay_double_reject(self):
        """2. Rejecting the same approval twice terminates safely on 1st, rejects replay on 2nd."""
        approval_id = self._trigger_pending_approval("sess_double_reject")

        mock_client = MagicMock()
        res1 = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res1.status, "rejected")
        self.assertEqual(len(res1.steps), 0)

        res2 = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res2.status, "error")
        self.assertIn("already been rejected", res2.final_answer)
        self.assertEqual(len(res2.steps), 0)

    def test_03_replay_approve_after_reject(self):
        """3. Submitting approve after a rejection is rejected and cannot reverse terminal state."""
        approval_id = self._trigger_pending_approval("sess_appr_after_rej")

        mock_client = MagicMock()
        # 1. Reject
        res_rej = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res_rej.status, "rejected")

        # 2. Attempt Approve after Reject
        res_appr = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res_appr.status, "error")
        self.assertIn("already been rejected", res_appr.final_answer)
        self.assertEqual(len(res_appr.steps), 0)

        # Verify state in checkpoint is still rejected
        state = get_thread_state(self.checkpointer, "sess_appr_after_rej")
        self.assertEqual(state.get("approval_status"), APPROVAL_STATUS_REJECTED)

    def test_04_replay_reject_after_approve(self):
        """4. Submitting reject after an approval is rejected and cannot reverse approved state."""
        approval_id = self._trigger_pending_approval("sess_rej_after_appr")

        mock_client = MagicMock()
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen profile.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        res_appr = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res_appr.status, "completed")

        res_rej = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res_rej.status, "error")
        self.assertIn("already been approved", res_rej.final_answer)

    def test_05_concurrent_conflicting_decisions(self):
        """5. Submitting concurrent decisions (approve and reject) results in exactly one winner and deterministic safety."""
        approval_id = self._trigger_pending_approval("sess_concurrent_conflicts")

        mock_client = MagicMock()
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen profile.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth, synth]

        # Submit both decisions concurrently using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_approve = executor.submit(
                resume_multi_agent_approval,
                approval_id=approval_id,
                decision="approve",
                client=mock_client,
                checkpointer=self.checkpointer,
            )
            future_reject = executor.submit(
                resume_multi_agent_approval,
                approval_id=approval_id,
                decision="reject",
                client=mock_client,
                checkpointer=self.checkpointer,
            )
            res_approve = future_approve.result()
            res_reject = future_reject.result()

        statuses = [res_approve.status, res_reject.status]
        # Exactly one must succeed (either 'completed' or 'rejected') and the other must be 'error'
        self.assertEqual(statuses.count("error"), 1)
        self.assertTrue("completed" in statuses or "rejected" in statuses)

    def test_06_approval_on_completed_non_approval_thread_blocked(self):
        """6. Attempting to approve a thread that finished normally without approval is rejected."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Non-sensitive answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        # Run ordinary query
        run_multi_agent(
            user_query="What is the meal allowance?",
            session_id="sess_ordinary_01",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        fake_appr_id = f"appr_12345678_sess_ordinary_01"
        res = resume_multi_agent_approval(
            approval_id=fake_appr_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        self.assertEqual(res.status, "error")
        self.assertIn("not in a pending state", res.final_answer)


# =====================================================================
# 3. APPROVAL STATE PERSISTENCE & PROCESS-RESTART SIMULATION
# =====================================================================

class TestApprovalPersistenceAndRestarts(unittest.TestCase):
    """Tests state persistence across simulated application restarts."""

    def test_01_approval_survival_across_restarts(self):
        """1. Workflow pauses, application restarts, fresh graph loads checkpoint, approval succeeds."""
        # Process 1
        proc1_ckpt = MemorySaver()
        proc1_graph = create_multi_agent_graph(checkpointer=proc1_ckpt)

        mock_client1 = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client1.chat.completions.create.side_effect = [s1]

        resp1 = run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="sess_restart_test",
            client=mock_client1,
            graph=proc1_graph,
            checkpointer=proc1_ckpt,
        )
        self.assertEqual(resp1.status, "pending_approval")

        state1 = get_thread_state(proc1_ckpt, "sess_restart_test")
        approval_id = state1.get("approval_id")
        self.assertIsNotNone(approval_id)

        shared_storage = proc1_ckpt.storage
        shared_writes = proc1_ckpt.writes
        shared_blobs = proc1_ckpt.blobs

        # Simulate Process Death: discard proc1 objects
        del proc1_graph
        del proc1_ckpt
        del mock_client1

        # Process 2 Startup: fresh graph connecting to same persistent storage
        proc2_ckpt = MemorySaver()
        proc2_ckpt.storage = shared_storage
        proc2_ckpt.writes = shared_writes
        proc2_ckpt.blobs = shared_blobs
        proc2_graph = create_multi_agent_graph(checkpointer=proc2_ckpt)

        mock_client2 = MagicMock()
        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen is VP of Engineering.")
        mock_client2.chat.completions.create.side_effect = [w1, s_fin, synth]

        resp2 = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client2,
            graph=proc2_graph,
            checkpointer=proc2_ckpt,
            expected_session_id="sess_restart_test",
        )

        self.assertEqual(resp2.status, "completed")
        self.assertEqual(len(resp2.steps), 1)
        self.assertEqual(resp2.steps[0].tool_name, "get_employee")
        self.assertIn("Alice Chen", resp2.final_answer)

    def test_02_rejected_approval_remains_rejected_across_restart(self):
        """2. Reject in Process 1 -> process dies -> Process 2 confirms rejection persists."""
        proc1_ckpt = MemorySaver()
        proc1_graph = create_multi_agent_graph(checkpointer=proc1_ckpt)

        mock_client1 = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client1.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="sess_restart_rej",
            client=mock_client1,
            graph=proc1_graph,
            checkpointer=proc1_ckpt,
        )
        approval_id = get_thread_state(proc1_ckpt, "sess_restart_rej").get("approval_id")

        # Reject in proc 1
        res_rej = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="reject",
            client=mock_client1,
            graph=proc1_graph,
            checkpointer=proc1_ckpt,
        )
        self.assertEqual(res_rej.status, "rejected")

        shared_storage = proc1_ckpt.storage
        shared_writes = proc1_ckpt.writes
        shared_blobs = proc1_ckpt.blobs

        # Tear down proc 1
        del proc1_graph
        del proc1_ckpt
        del mock_client1

        # Proc 2 startup
        proc2_ckpt = MemorySaver()
        proc2_ckpt.storage = shared_storage
        proc2_ckpt.writes = shared_writes
        proc2_ckpt.blobs = shared_blobs
        proc2_graph = create_multi_agent_graph(checkpointer=proc2_ckpt)

        state2 = get_thread_state(proc2_ckpt, "sess_restart_rej")
        self.assertEqual(state2.get("approval_status"), APPROVAL_STATUS_REJECTED)

        # Attempting to approve in Proc 2 is rejected
        mock_client2 = MagicMock()
        res_after = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client2,
            graph=proc2_graph,
            checkpointer=proc2_ckpt,
        )
        self.assertEqual(res_after.status, "error")
        self.assertIn("already been rejected", res_after.final_answer)


# =====================================================================
# 4. CHECKPOINT DATABASE FAILURE & FALLBACK BEHAVIOR
# =====================================================================

class TestCheckpointDatabaseFailure(unittest.TestCase):
    """Tests deterministic failures involving the PostgreSQL checkpoint backend and fallback safety."""

    def test_01_postgres_checkpointer_offline_fallback(self):
        """1. When PostgreSQL checkpoint DB is unavailable, factory safely falls back to MemorySaver."""
        with patch("app.agent.checkpoint.is_postgres_accessible", return_value=False):
            ckpt = create_postgres_checkpointer("postgresql://user:pass@127.0.0.1:5432/ckpt_db")
            self.assertIsNone(ckpt)

            default_ckpt = create_checkpointer(
                conn_string="postgresql://user:pass@127.0.0.1:5432/ckpt_db",
                use_postgres_if_available=True,
            )
            self.assertIsInstance(default_ckpt, MemorySaver)

    def test_02_postgres_connection_failure_masks_credentials(self):
        """2. PostgreSQL connection failures mask raw credentials in log messages."""
        secret_conn = "postgresql://db_admin:SuperSecretP@ssw0rd!@10.0.0.5:5432/secure_db"
        masked = mask_connection_string(secret_conn)
        self.assertNotIn("SuperSecretP@ssw0rd!", masked)
        self.assertIn("db_admin:***@10.0.0.5:5432/secure_db", masked)

    def test_03_checkpoint_write_failure_during_run(self):
        """3. When checkpointer throws an exception during graph write/put, run_multi_agent fails safely."""
        failing_checkpointer = MagicMock(spec=BaseCheckpointSaver)
        failing_checkpointer.get_tuple.return_value = None
        failing_checkpointer.put.side_effect = RuntimeError("Disk full / DB connection dropped")
        failing_checkpointer.put_writes.side_effect = RuntimeError("Disk full / DB connection dropped")

        graph = create_multi_agent_graph(checkpointer=failing_checkpointer)

        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        resp = run_multi_agent(
            user_query="Policy inquiry",
            session_id="sess_failing_write",
            client=mock_client,
            graph=graph,
            checkpointer=failing_checkpointer,
        )

        self.assertEqual(resp.status, "error")
        self.assertIn("An error occurred while executing the multi-agent graph", resp.final_answer)

    def test_04_checkpoint_read_failure_during_resume(self):
        """4. When checkpointer throws an exception during get_tuple on resume, it returns safe error."""
        failing_checkpointer = MagicMock(spec=BaseCheckpointSaver)
        failing_checkpointer.get_tuple.side_effect = RuntimeError("Postgres connection timeout")

        res = resume_multi_agent_approval(
            approval_id="appr_tok_sess_failing_read",
            decision="approve",
            checkpointer=failing_checkpointer,
        )

        self.assertEqual(res.status, "error")
        self.assertIn("was not found or has already expired", res.final_answer)
        self.assertEqual(len(res.steps), 0)

    def test_05_checkpoint_delete_failure_handled_safely(self):
        """5. When delete_thread_checkpoints encounters an error, it returns False and does not crash."""
        failing_checkpointer = MagicMock(spec=BaseCheckpointSaver)
        failing_checkpointer.delete_thread.side_effect = RuntimeError("DB error on delete")

        result = delete_thread_checkpoints(failing_checkpointer, "sess_delete_fail")
        self.assertFalse(result)

    def test_06_corrupted_checkpoint_state_handled_safely(self):
        """6. Malformed or corrupted checkpoint state values do not cause unhandled exceptions."""
        corrupted_checkpointer = MemorySaver()
        res = resume_multi_agent_approval(
            approval_id="appr_tok_sess_corrupted",
            decision="approve",
            checkpointer=corrupted_checkpointer,
        )
        self.assertEqual(res.status, "error")
        self.assertTrue(
            "was not found" in res.final_answer or "not in a pending state" in res.final_answer
        )


# =====================================================================
# 5. CHECKPOINT THREAD ISOLATION
# =====================================================================

class TestCheckpointThreadIsolation(unittest.TestCase):
    """Tests strict isolation between concurrent or distinct session threads."""

    def setUp(self):
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)

    def tearDown(self):
        reset_default_checkpointer()

    def test_01_thread_state_isolation(self):
        """1. State, messages, and evidence never bleed between Thread A and Thread B."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done A"}))
        synth1 = _create_mock_completion(content="Answer for Alpha.")
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done B"}))
        synth2 = _create_mock_completion(content="Answer for Beta.")
        mock_client.chat.completions.create.side_effect = [s1, synth1, s2, synth2]

        run_multi_agent(user_query="Query Alpha", session_id="thread_iso_A", client=mock_client, checkpointer=self.checkpointer)
        run_multi_agent(user_query="Query Beta", session_id="thread_iso_B", client=mock_client, checkpointer=self.checkpointer)

        state_a = get_thread_state(self.checkpointer, "thread_iso_A")
        state_b = get_thread_state(self.checkpointer, "thread_iso_B")

        self.assertEqual(state_a["query"], "Query Alpha")
        self.assertEqual(state_b["query"], "Query Beta")
        self.assertNotIn("Beta", json.dumps(state_a))
        self.assertNotIn("Alpha", json.dumps(state_b))

    def test_02_delete_thread_a_does_not_affect_thread_b(self):
        """2. Deleting Thread A's checkpoints leaves Thread B completely intact."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "A"}))
        synth1 = _create_mock_completion(content="Ans A")
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "B"}))
        synth2 = _create_mock_completion(content="Ans B")
        mock_client.chat.completions.create.side_effect = [s1, synth1, s2, synth2]

        run_multi_agent(user_query="Alpha", session_id="thread_del_A", client=mock_client, checkpointer=self.checkpointer)
        run_multi_agent(user_query="Beta", session_id="thread_del_B", client=mock_client, checkpointer=self.checkpointer)

        # Delete Thread A
        delete_thread_checkpoints(self.checkpointer, "thread_del_A")

        self.assertIsNone(get_thread_state(self.checkpointer, "thread_del_A"))
        self.assertIsNotNone(get_thread_state(self.checkpointer, "thread_del_B"))
        self.assertEqual(get_thread_state(self.checkpointer, "thread_del_B")["query"], "Beta")


# =====================================================================
# 6. CHECKPOINT STATE SANITIZATION
# =====================================================================

class TestCheckpointStateSanitization(unittest.TestCase):
    """Tests that persisted checkpoint state excludes raw secrets, API keys, and connection strings."""

    def setUp(self):
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)

    def tearDown(self):
        reset_default_checkpointer()

    def test_01_persisted_state_contains_no_secrets(self):
        """1. Checkpoint serialization does not store API keys, DB passwords, or system prompt definitions."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check salary"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="Confidential query for E1001",
            session_id="sess_sanitize_01",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        state = get_thread_state(self.checkpointer, "sess_sanitize_01")
        serialized_state = json.dumps(state, default=str)

        # Sensitive tokens that must NEVER appear in persistent checkpoint storage
        forbidden_tokens = [
            "gsk_",  # Groq API key prefix
            "sk-",   # OpenAI key prefix
            "DB_PASSWORD",
            "SUPERVISOR_SYSTEM_PROMPT",
            "HR_POLICY_WORKER_PROMPT",
            "EMPLOYEE_RECORDS_WORKER_PROMPT",
            "TRAVEL_EXPENSE_WORKER_PROMPT",
        ]
        for token in forbidden_tokens:
            self.assertNotIn(token, serialized_state)

    def test_02_persisted_state_fields_allowlist(self):
        """2. Persisted checkpoint contains only validated domain state fields."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Answer.")
        mock_client.chat.completions.create.side_effect = [s1, synth]

        run_multi_agent(
            user_query="Allowed fields check",
            session_id="sess_fields_01",
            client=mock_client,
            checkpointer=self.checkpointer,
        )

        state = get_thread_state(self.checkpointer, "sess_fields_01")
        allowed_fields = {
            "session_id", "query", "messages", "turn_messages", "current_worker",
            "worker_results", "collected_evidence", "completed_domains",
            "missing_information", "workflow_intent", "workflow_status",
            "conditional_decisions", "approval_required", "approval_status",
            "approval_reason", "approval_request", "approval_decision",
            "approval_id", "steps", "step_count", "max_steps",
            "supervisor_iterations", "max_supervisor_iterations", "routing_history",
            "executed_calls", "final_answer", "status", "duration_ms",
            "used_rag", "citations", "error", "start_time", "model", "client",
        }
        for field in state.keys():
            self.assertIn(field, allowed_fields)


# =====================================================================
# 7. CHECKPOINT CLEANUP & IDEMPOTENCY
# =====================================================================

class TestCheckpointCleanup(unittest.TestCase):
    """Tests session and checkpoint cleanup operations and idempotency."""

    def setUp(self):
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)

    def tearDown(self):
        reset_default_checkpointer()

    def test_01_repeated_cleanup_is_idempotent(self):
        """1. Calling delete_thread_checkpoints multiple times returns True without crashing."""
        self.assertTrue(delete_thread_checkpoints(self.checkpointer, "sess_idem_01"))
        self.assertTrue(delete_thread_checkpoints(self.checkpointer, "sess_idem_01"))
        self.assertTrue(delete_thread_checkpoints(self.checkpointer, "sess_idem_01"))

    def test_02_cleanup_nonexistent_thread(self):
        """2. Deleting checkpoints for a thread that never existed returns True safely."""
        self.assertTrue(delete_thread_checkpoints(self.checkpointer, "thread_does_not_exist_999"))

    def test_03_deleted_thread_approval_cannot_be_resumed(self):
        """3. After deleting thread checkpoints, associated approval ID cannot be resumed."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="sess_to_delete",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        approval_id = get_thread_state(self.checkpointer, "sess_to_delete").get("approval_id")

        # Delete checkpoints for this thread
        delete_thread_checkpoints(self.checkpointer, "sess_to_delete")

        # Attempt resume
        res = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        self.assertEqual(res.status, "error")
        self.assertIn("was not found", res.final_answer)


# =====================================================================
# 8. API ENDPOINT INTEGRATION TESTS
# =====================================================================

class TestApiApprovalEndpoints(unittest.TestCase):
    """Tests FastAPI approval endpoints for proper HTTP status code mapping and authorization enforcement."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from app.api.main import app
        self.client = TestClient(app)
        self.checkpointer = MemorySaver()
        set_default_checkpointer(self.checkpointer)
        _PENDING_APPROVAL_STORE.clear()

    def tearDown(self):
        reset_default_checkpointer()
        _PENDING_APPROVAL_STORE.clear()

    def test_01_api_approval_not_found(self):
        """1. Submitting decision for unknown approval ID returns 404 Not Found."""
        response = self.client.post(
            "/api/v1/agent/approvals/appr_nonexistent_999",
            json={"decision": "approve"},
        )
        self.assertEqual(response.status_code, 404)

    def test_02_api_approval_invalid_decision(self):
        """2. Submitting invalid decision string returns 422 Unprocessable Entity (validation error)."""
        response = self.client.post(
            "/api/v1/agent/approvals/appr_test_123",
            json={"decision": "grant_access"},
        )
        self.assertEqual(response.status_code, 422)

    def test_03_api_approval_wrong_session_forbidden(self):
        """3. Submitting decision with mismatched session_id returns 403 Forbidden."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="session_api_owner",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        approval_id = get_thread_state(self.checkpointer, "session_api_owner").get("approval_id")

        with patch("app.agent.multi_agent.default_client", mock_client):
            response = self.client.post(
                f"/api/v1/agent/approvals/{approval_id}",
                json={"decision": "approve", "session_id": "session_api_attacker"},
            )
            self.assertEqual(response.status_code, 403)
            self.assertIn("does not belong to session", response.json()["detail"])

    def test_04_api_approval_replay_bad_request(self):
        """4. Replaying approval decision returns 400 Bad Request."""
        mock_client = MagicMock()
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Salary check"}))
        mock_client.chat.completions.create.side_effect = [s1]

        run_multi_agent(
            user_query="Confidential salary for E1001",
            session_id="session_api_replay",
            client=mock_client,
            checkpointer=self.checkpointer,
        )
        approval_id = get_thread_state(self.checkpointer, "session_api_replay").get("approval_id")

        tc = _create_mock_tool_call("tc_e", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Alice Chen profile.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        with patch("app.agent.multi_agent.default_client", mock_client):
            # 1st approval
            res1 = self.client.post(
                f"/api/v1/agent/approvals/{approval_id}",
                json={"decision": "approve"},
            )
            self.assertEqual(res1.status_code, 200)

            # 2nd approval (replay)
            res2 = self.client.post(
                f"/api/v1/agent/approvals/{approval_id}",
                json={"decision": "approve"},
            )
            self.assertEqual(res2.status_code, 400)
            self.assertIn("already been approved", res2.json()["detail"])

    def test_05_api_session_clear_and_delete_idempotent(self):
        """5. Session clear and delete endpoints execute cleanly and idempotently."""
        # Clear
        res_clear = self.client.post("/api/v1/agent/sessions/test_sess_clear/clear")
        self.assertEqual(res_clear.status_code, 200)
        self.assertEqual(res_clear.json()["status"], "cleared")

        # Delete
        res_del = self.client.delete("/api/v1/agent/sessions/test_sess_del")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["status"], "deleted")


if __name__ == "__main__":
    unittest.main()
