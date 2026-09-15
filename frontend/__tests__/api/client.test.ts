import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { EnterpriseApiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import {
  mockHealthResponse,
  mockAskSuccessResponse,
} from '../fixtures/policyFixtures';
import {
  mockEmployeeRecord,
  mockLeaveRecord,
  mockTravelRecord,
  mockAgentSuccessResponse,
  mockApprovalApprovedDecision,
  mockSessionClearResponse,
} from '../fixtures/agentFixtures';

describe('EnterpriseApiClient', () => {
  let client: EnterpriseApiClient;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    client = new EnterpriseApiClient('http://localhost:8000', 5000);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('initializes base URL and trims trailing slashes', () => {
    const customClient = new EnterpriseApiClient('http://api.enterprise.com///');
    expect(customClient.getBaseUrl()).toBe('http://api.enterprise.com');
    customClient.setBaseUrl('http://new-url.local/');
    expect(customClient.getBaseUrl()).toBe('http://new-url.local');
  });

  describe('healthCheck', () => {
    it('executes GET /health and returns parsed JSON', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockHealthResponse,
      });

      const res = await client.healthCheck();
      expect(res).toEqual(mockHealthResponse);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/health',
        expect.objectContaining({
          method: 'GET',
          cache: 'no-store',
        })
      );
    });
  });

  describe('askPolicyQuestion', () => {
    it('executes POST /api/v1/ask with JSON payload', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockAskSuccessResponse,
      });

      const res = await client.askPolicyQuestion({ question: 'meal per diem' });
      expect(res).toEqual(mockAskSuccessResponse);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ask',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ question: 'meal per diem' }),
        })
      );
    });
  });

  describe('structured employee endpoints', () => {
    it('executes GET /api/v1/employees/:id with URL encoding', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockEmployeeRecord,
      });

      const res = await client.getEmployee('E1001 ');
      expect(res).toEqual(mockEmployeeRecord);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/employees/E1001',
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('executes GET /api/v1/employees/:id/leave', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockLeaveRecord,
      });

      const res = await client.getEmployeeLeave('E1001');
      expect(res).toEqual(mockLeaveRecord);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/employees/E1001/leave',
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('executes GET /api/v1/employees/:id/travel', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockTravelRecord,
      });

      const res = await client.getEmployeeTravel('E1001');
      expect(res).toEqual(mockTravelRecord);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/employees/E1001/travel',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('agent endpoints', () => {
    it('executes POST /api/v1/agent/chat', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockAgentSuccessResponse,
      });

      const res = await client.agentChat({
        session_id: 'session-test-123',
        message: 'How much spent on travel?',
      });
      expect(res).toEqual(mockAgentSuccessResponse);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/agent/chat',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            session_id: 'session-test-123',
            message: 'How much spent on travel?',
          }),
        })
      );
    });

    it('executes POST /api/v1/agent/sessions/:id/clear', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockSessionClearResponse,
      });

      const res = await client.clearSession('session-test-123');
      expect(res).toEqual(mockSessionClearResponse);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/agent/sessions/session-test-123/clear',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('executes DELETE /api/v1/agent/sessions/:id', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ session_id: 'session-test-123', status: 'deleted', message: 'Deleted' }),
      });

      const res = await client.deleteSession('session-test-123');
      expect(res.status).toBe('deleted');
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/agent/sessions/session-test-123',
        expect.objectContaining({ method: 'DELETE' })
      );
    });

    it('executes POST /api/v1/agent/approvals/:id', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockApprovalApprovedDecision,
      });

      const res = await client.submitApprovalDecision('appr_req_789', {
        decision: 'approve',
        notes: 'Authorized by director',
      });
      expect(res).toEqual(mockApprovalApprovedDecision);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/agent/approvals/appr_req_789',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            decision: 'approve',
            notes: 'Authorized by director',
          }),
        })
      );
    });
  });

  describe('error and resilience handling', () => {
    it('handles 404 response safely with ApiClientError', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: "Employee 'E9999' not found", error_type: 'NotFoundError' }),
      });

      await expect(client.getEmployee('E9999')).rejects.toThrow(ApiClientError);
      try {
        await client.getEmployee('E9999');
      } catch (err) {
        const error = err as ApiClientError;
        expect(error.statusCode).toBe(404);
        expect(error.errorType).toBe('NotFoundError');
        expect(error.userMessage).toContain("Employee 'E9999' not found");
      }
    });

    it('handles 422 validation errors with formatted array details', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          detail: [{ loc: ['body', 'question'], msg: 'Field required', type: 'value_error.missing' }],
        }),
      });

      await expect(client.askPolicyQuestion({ question: '' })).rejects.toThrow(ApiClientError);
      try {
        await client.askPolicyQuestion({ question: '' });
      } catch (err) {
        const error = err as ApiClientError;
        expect(error.statusCode).toBe(422);
        expect(error.errorType).toBe('ValidationError');
        expect(error.userMessage).toContain('Field required');
      }
    });

    it('handles 500 internal database error with sanitized user message', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          detail: 'FATAL: database connection refused postgresql://user:secret@db:5432/db',
          error_type: 'DatabaseError',
        }),
      });

      try {
        await client.getEmployee('E1001');
      } catch (err) {
        const error = err as ApiClientError;
        expect(error.statusCode).toBe(500);
        expect(error.errorType).toBe('DatabaseError');
        expect(error.userMessage).toBe('A database error occurred while processing your request. Please try again later.');
        expect(error.userMessage).not.toContain('secret');
      }
    });

    it('handles network failure (backend offline)', async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

      try {
        await client.healthCheck();
      } catch (err) {
        const error = err as ApiClientError;
        expect(error.statusCode).toBe(0);
        expect(error.errorType).toBe('ServiceUnavailable');
        expect(error.userMessage).toContain('backend service is currently unreachable');
      }
    });

    it('handles non-JSON error response gracefully', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        headers: new Headers({ 'content-type': 'text/html' }),
        json: async () => {
          throw new Error('Not JSON');
        },
        text: async () => '<html><body>Bad Gateway</body></html>',
      });

      try {
        await client.healthCheck();
      } catch (err) {
        const error = err as ApiClientError;
        expect(error.statusCode).toBe(502);
      }
    });
  });
});
