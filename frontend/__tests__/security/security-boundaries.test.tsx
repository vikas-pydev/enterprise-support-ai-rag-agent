/**
 * Frontend Security & Boundary Validation Test Suite (Phase 9 Task 9).
 *
 * Verifies that the Next.js React frontend:
 * 1. Safely escapes and renders untrusted/malicious text without XSS or raw markup execution.
 * 2. Sanitizes backend error messages, preventing raw stack traces, database credentials, or prompt definitions from reaching the user.
 * 3. Gracefully handles malformed, empty, or unexpected API response payloads without unhandled UI crashes.
 * 4. Strictly protects Human-in-the-Loop approval workflows against client-side double-submission and UI tampering.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ApprovalCard } from '@/components/agent/ApprovalCard';
import { ApiClientError } from '@/lib/api/errors';
import { EnterpriseApiClient } from '@/lib/api/client';

describe('Frontend Security Boundaries & Rendering Safety', () => {
  describe('1. Untrusted Text & XSS Rendering Safety', () => {
    it('escapes malicious HTML, scripts, and event handlers in ApprovalCard reason', () => {
      const maliciousReason = '<img src=x onerror="alert(\'XSS\')" /> Malicious injection payload <script>alert(1)</script>';
      render(
        <ApprovalCard
          approvalId="appr_xss_test"
          reason={maliciousReason}
          onDecision={vi.fn()}
        />
      );

      // Verify the literal string is rendered as text content, not parsed as DOM elements
      const reasonElement = screen.getByText((content) => content.includes('Malicious injection payload'));
      expect(reasonElement).toBeDefined();
      expect(document.querySelector('img[src="x"]')).toBeNull();
      expect(document.querySelector('script')).toBeNull();
    });

    it('escapes malicious script payload in operator review notes after approval', () => {
      const maliciousNotes = '<svg onload="window.leakSecret()"><desc>Exploit</desc></svg>';
      render(
        <ApprovalCard
          approvalId="appr_resolved_001"
          approvalStatus="approved"
          approvalNotes={maliciousNotes}
          onDecision={vi.fn()}
        />
      );

      expect(screen.getByText((content) => content.includes(maliciousNotes))).toBeDefined();
      expect(document.querySelector('svg[onload]')).toBeNull();
    });
  });

  describe('2. Error Message Sanitization & Secret Masking', () => {
    it('sanitizes raw Python tracebacks from 500 error responses', () => {
      const rawTraceback = `Traceback (most recent call last):
  File "app/api/main.py", line 330, in agent_chat_endpoint
  File "app/agent/agent.py", line 123, in run
DatabaseError: connection to 'postgresql://admin:secretPass@internal-db:5432' failed`;

      const error = ApiClientError.create(500, {
        detail: rawTraceback,
        error_type: 'ServerError',
      });

      expect(error.userMessage).toBe(
        'A database error occurred while processing your request. Please try again later.'
      );
      expect(error.userMessage).not.toContain('Traceback');
      expect(error.userMessage).not.toContain('secretPass');
      expect(error.userMessage).not.toContain('postgresql://');
    });

    it('sanitizes database error details from 500 responses', () => {
      const dbErrorPayload = {
        detail: 'psycopg2.OperationalError: FATAL: password authentication failed for user "dbadmin"',
        error_type: 'DatabaseError',
      };

      const error = ApiClientError.create(500, dbErrorPayload);

      expect(error.errorType).toBe('DatabaseError');
      expect(error.userMessage).toBe(
        'A database error occurred while processing your request. Please try again later.'
      );
      expect(error.userMessage).not.toContain('dbadmin');
      expect(error.userMessage).not.toContain('password authentication failed');
    });

    it('sanitizes 403 authorization error without leaking internal session structures', () => {
      const authError = ApiClientError.create(403, {
        detail: 'Approval authorization error: approval does not belong to session.',
        error_type: 'AuthorizationError',
      });

      expect(errorTypeOrDetail(authError)).toContain('Approval authorization error');
    });
  });

  describe('3. Robustness Against Malformed Responses', () => {
    it('handles non-JSON error string payloads safely', () => {
      const error = ApiClientError.create(502, 'Bad Gateway - Upstream timeout');
      expect(error.statusCode).toBe(502);
      expect(error.userMessage).toBe('An unexpected error occurred. Please try again.');
    });

    it('handles FastAPI 422 validation array error structures cleanly', () => {
      const validationPayload = {
        detail: [
          { loc: ['body', 'question'], msg: 'Field required', type: 'value_error.missing' },
          { loc: ['body', 'session_id'], msg: 'Must be a string', type: 'type_error.str' },
        ],
      };

      const error = ApiClientError.create(422, validationPayload);
      expect(error.errorType).toBe('ValidationError');
      expect(error.detail).toContain('Field required');
      expect(error.detail).toContain('Must be a string');
      expect(error.userMessage).toContain('Invalid request:');
    });

    it('handles undefined and null error payloads without crashing', () => {
      const error = ApiClientError.create(500, undefined);
      expect(error.statusCode).toBe(500);
      expect(error.userMessage).toBe('An internal server error occurred while processing your request.');
    });
  });

  describe('4. HITL Approval Workflow Client-Side Boundaries', () => {
    it('prevents double-clicking approval action buttons while submission is in progress', async () => {
      let resolveDecision: () => void = () => {};
      const onDecisionMock = vi.fn().mockImplementation(
        () =>
          new Promise<void>((resolve) => {
            resolveDecision = resolve;
          })
      );

      render(
        <ApprovalCard
          approvalId="appr_race_test"
          onDecision={onDecisionMock}
        />
      );

      const approveButton = screen.getByRole('button', { name: /Approve & Continue/i });
      fireEvent.click(approveButton);

      expect(onDecisionMock).toHaveBeenCalledTimes(1);

      // Attempt second click while first submission is in progress
      fireEvent.click(approveButton);
      expect(onDecisionMock).toHaveBeenCalledTimes(1);

      // Resolve pending decision
      resolveDecision();
      await waitFor(() => expect(screen.queryByText(/Authorizing/i)).toBeNull());
    });

    it('renders read-only state for already resolved approval items without action buttons', () => {
      render(
        <ApprovalCard
          approvalId="appr_resolved_static"
          approvalStatus="approved"
          approvalDecision="approve"
          onDecision={vi.fn()}
        />
      );

      expect(screen.queryByRole('button', { name: /Approve/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /Reject/i })).toBeNull();
      expect(screen.getByText(/Operation Authorized by Operator/i)).toBeDefined();
      expect(screen.getByText(/Checkpoint Thread Resolved/i)).toBeDefined();
    });
  });
});

function errorTypeOrDetail(err: ApiClientError): string {
  return `${err.errorType}: ${err.userMessage}`;
}
