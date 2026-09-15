import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { EnterpriseApiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { startIntegrationServer, stopIntegrationServer } from './testServerHelper';

describe('FastAPI ↔ Next.js Agent Chat & HITL Integration', () => {
  let client: EnterpriseApiClient;

  beforeAll(async () => {
    const baseUrl = await startIntegrationServer();
    client = new EnterpriseApiClient(baseUrl);
  }, 35000);

  // -------------------------------------------------------------------
  // 1. Agent Multi-Turn Chat Integration
  // -------------------------------------------------------------------
  describe('Agent Chat Endpoint (POST /api/v1/agent/chat)', () => {
    it('executes first turn successfully, parsing steps and execution trace', async () => {
      const sessionId = 'session_turn_1_test';
      const res = await client.agentChat({
        session_id: sessionId,
        message: 'What is the employee profile for E1001?',
      });

      expect(res).toBeDefined();
      expect(res.session_id).toBe(sessionId);
      expect(res.status).toBe('completed');
      expect(typeof res.answer).toBe('string');
      expect(res.answer).toContain('Alice Chen');
      expect(res.total_steps).toBe(1);
      expect(Array.isArray(res.steps)).toBe(true);
      expect(res.steps.length).toBe(1);

      // Verify step structure
      const step = res.steps[0];
      expect(step.step_number).toBe(1);
      expect(step.tool_name).toBe('get_employee_profile_tool');
      expect(step.tool_args).toHaveProperty('employee_id', 'E1001');
      expect(step.status).toBe('success');
      expect(typeof step.duration_ms).toBe('number');

      // Verify trace structure
      expect(res.trace).toBeDefined();
      expect(res.trace?.session_id).toBe(sessionId);
      expect(res.trace?.total_steps).toBe(1);
      expect(res.trace?.tools_invoked).toContain('get_employee_profile_tool');
      expect(res.trace?.status).toBe('completed');
    });

    it('executes follow-up turn in same session with context continuity', async () => {
      const sessionId = 'session_multiturn_flow';

      // Turn 1
      await client.agentChat({
        session_id: sessionId,
        message: 'Tell me about employee E1001.',
      });

      // Turn 2
      const turn2 = await client.agentChat({
        session_id: sessionId,
        message: 'What is her leave balance?',
      });

      expect(turn2.session_id).toBe(sessionId);
      expect(turn2.status).toBe('completed');
      expect(turn2.answer).toContain('24');
      expect(turn2.steps[0].tool_name).toBe('get_employee_leave_tool');
    });

    it('maintains strict isolation between distinct sessions', async () => {
      const sessionA = 'session_user_alice';
      const sessionB = 'session_user_bob';

      const resA = await client.agentChat({
        session_id: sessionA,
        message: 'Show details for E1001.',
      });
      const resB = await client.agentChat({
        session_id: sessionB,
        message: 'Show details for E1002.',
      });

      expect(resA.session_id).toBe(sessionA);
      expect(resB.session_id).toBe(sessionB);
      expect(resA.session_id).not.toBe(resB.session_id);
    });

    it('rejects invalid/empty session_id or message with 422 ValidationError', async () => {
      try {
        await client.agentChat({ session_id: '', message: 'Hello' });
        expect.unreachable('Should have failed on empty session_id');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(422);
        expect(apiErr.errorType).toBe('ValidationError');
      }

      try {
        await client.agentChat({ session_id: 'valid_sess', message: '   ' });
        expect.unreachable('Should have failed on empty message');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(422);
        expect(apiErr.errorType).toBe('ValidationError');
      }
    });
  });

  // -------------------------------------------------------------------
  // 2. Human-in-the-Loop (HITL) Approvals
  // -------------------------------------------------------------------
  describe('Human-in-the-Loop Approvals (POST /api/v1/agent/approvals/{id})', () => {
    it('triggers pending_approval state and resumes with approved decision', async () => {
      const sessionId = 'session_test_approval';

      // 1. Agent asks for approval
      const chatRes = await client.agentChat({
        session_id: sessionId,
        message: 'Cancel all pending travel claims for E1001.',
      });

      expect(chatRes.status).toBe('pending_approval');

      // 2. Submit approval decision
      const apprDecision = await client.submitApprovalDecision('appr_req_1001', {
        decision: 'approve',
        session_id: sessionId,
        notes: 'Manager approved travel cancellation.',
      });

      expect(apprDecision).toBeDefined();
      expect(apprDecision.approval_id).toBe('appr_req_1001');
      expect(apprDecision.decision).toBe('approve');
      expect(apprDecision.status).toBe('completed');
      expect(apprDecision.answer).toContain('Approval granted');
      expect(apprDecision.trace?.status).toBe('completed');
    });

    it('rejects approval decision replay on already resolved request with 400 Bad Request', async () => {
      // Re-submitting decision on already resolved approval request
      try {
        await client.submitApprovalDecision('appr_req_1001', {
          decision: 'approve',
          session_id: 'session_test_approval',
        });
        expect.unreachable('Should have failed on duplicate approval replay');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(400);
        expect(apiErr.errorType).toBe('ValidationError');
        expect(apiErr.userMessage).toContain('not in a pending state');
      }
    });

    it('enforces session ownership returning 403 AuthorizationError on session mismatch', async () => {
      // Seed another pending approval
      const validSession = 'session_legitimate_owner';
      await client.agentChat({
        session_id: validSession,
        message: 'Cancel travel claims for E1001',
      });

      try {
        await client.submitApprovalDecision('appr_req_1001', {
          decision: 'approve',
          session_id: 'session_attacker_impersonator',
        });
        expect.unreachable('Should have returned 403 on session mismatch');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(403);
        expect(apiErr.errorType).toBe('AuthorizationError');
        expect(apiErr.userMessage).toContain('does not belong to session');
      }
    });

    it('returns 404 NotFoundError for non-existent approval ID', async () => {
      try {
        await client.submitApprovalDecision('appr_nonexistent_9999', {
          decision: 'approve',
        });
        expect.unreachable('Should have returned 404 for missing approval');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(404);
        expect(apiErr.errorType).toBe('NotFoundError');
      }
    });
  });

  // -------------------------------------------------------------------
  // 3. Session Clear & Delete Integration
  // -------------------------------------------------------------------
  describe('Session Controls Integration', () => {
    it('clears session context via POST /api/v1/agent/sessions/{id}/clear', async () => {
      const sessionId = 'session_to_clear';
      await client.agentChat({
        session_id: sessionId,
        message: 'Remember my preferences.',
      });

      const clearRes = await client.clearSession(sessionId);
      expect(clearRes.session_id).toBe(sessionId);
      expect(clearRes.status).toBe('cleared');
      expect(clearRes.message).toContain('cleared');
    });

    it('deletes session completely via DELETE /api/v1/agent/sessions/{id}', async () => {
      const sessionId = 'session_to_delete';
      await client.agentChat({
        session_id: sessionId,
        message: 'Temporary session data.',
      });

      const delRes = await client.deleteSession(sessionId);
      expect(delRes.session_id).toBe(sessionId);
      expect(delRes.status).toBe('deleted');
      expect(delRes.message).toContain('deleted');
    });
  });

  // -------------------------------------------------------------------
  // 4. Security & Sanitization Boundary
  // -------------------------------------------------------------------
  describe('Error & Security Boundary Integration', () => {
    it('sanitizes unexpected agent errors into safe 500 without leaking system prompts or tracebacks', async () => {
      try {
        await client.agentChat({
          session_id: 'session_error_test',
          message: 'trigger_agent_error',
        });
        expect.unreachable('Should have failed with 500 error');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(500);
        expect(apiErr.userMessage).toContain('internal server error');

        // Verify security guarantees
        expect(apiErr.detail).not.toContain('GROQ_API_KEY');
        expect(apiErr.detail).not.toContain('OPENAI_API_KEY');
        expect(apiErr.detail).not.toContain('Traceback');
        expect(apiErr.userMessage).not.toContain('RuntimeError');
      }
    });
  });
});
