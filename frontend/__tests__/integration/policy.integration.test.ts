import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { EnterpriseApiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { startIntegrationServer, stopIntegrationServer } from './testServerHelper';

describe('FastAPI ↔ Next.js Policy RAG Integration (POST /api/v1/ask)', () => {
  let client: EnterpriseApiClient;

  beforeAll(async () => {
    const baseUrl = await startIntegrationServer();
    client = new EnterpriseApiClient(baseUrl);
  }, 35000);

  // -------------------------------------------------------------------
  // 1. Grounded Policy Response
  // -------------------------------------------------------------------
  describe('Successful Grounded Policy Query', () => {
    it('submits question and verifies grounded response with structured citations', async () => {
      const res = await client.askPolicyQuestion({
        question: 'What is the meal per diem allowance for domestic travel?',
      });

      expect(res).toBeDefined();
      expect(res.question).toBe('What is the meal per diem allowance for domestic travel?');
      expect(res.is_refusal).toBe(false);
      expect(typeof res.answer).toBe('string');
      expect(res.answer).toContain('$75');
      expect(Array.isArray(res.sources)).toBe(true);
      expect(res.sources.length).toBeGreaterThan(0);

      // Verify citation contract
      const citation = res.sources[0];
      expect(typeof citation.rank).toBe('number');
      expect(citation.rank).toBe(1);
      expect(typeof citation.title).toBe('string');
      expect(citation.title).toBe('Corporate Travel & Expense Policy');
      expect(citation.source_file.endsWith('.md')).toBe(true);
      expect(typeof citation.chunk_uid).toBe('string');
      expect(typeof citation.rerank_score).toBe('number');
      expect(citation.rerank_score).toBeGreaterThan(0);
      expect(typeof citation.snippet).toBe('string');
      expect(citation.snippet.length).toBeGreaterThan(0);
    });
  });

  // -------------------------------------------------------------------
  // 2. Unanswerable Out-of-Domain Refusal
  // -------------------------------------------------------------------
  describe('Out-of-Domain Policy Refusal', () => {
    it('returns strict refusal with empty citation list for unsupported policy queries', async () => {
      const res = await client.askPolicyQuestion({
        question: 'What is the company pet insurance reimbursement policy?',
      });

      expect(res).toBeDefined();
      expect(res.is_refusal).toBe(true);
      expect(res.sources).toEqual([]);
      expect(res.answer.toLowerCase()).toContain('not available in the provided documents');
    });
  });

  // -------------------------------------------------------------------
  // 3. Pydantic Validation (422) Boundary
  // -------------------------------------------------------------------
  describe('FastAPI Pydantic Validation (422)', () => {
    it('rejects empty question string with 422 ValidationError', async () => {
      try {
        await client.askPolicyQuestion({ question: '' });
        expect.unreachable('Should have rejected empty question');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(422);
        expect(apiErr.errorType).toBe('ValidationError');
        expect(apiErr.userMessage).toContain('Invalid request');
        // Ensure no internal backend Python traceback leaked
        expect(apiErr.detail).not.toContain('Traceback');
      }
    });

    it('rejects whitespace-only question string with 422 ValidationError', async () => {
      try {
        await client.askPolicyQuestion({ question: '     ' });
        expect.unreachable('Should have rejected whitespace-only question');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(422);
        expect(apiErr.errorType).toBe('ValidationError');
      }
    });
  });

  // -------------------------------------------------------------------
  // 4. Server Error Boundary
  // -------------------------------------------------------------------
  describe('Server Failure Handling', () => {
    it('handles simulated internal 500 error gracefully without leaking stack trace', async () => {
      try {
        await client.askPolicyQuestion({ question: 'trigger_500' });
        expect.unreachable('Should have failed on simulated 500');
      } catch (err: unknown) {
        expect(err).toBeInstanceOf(ApiClientError);
        const apiErr = err as ApiClientError;
        expect(apiErr.statusCode).toBe(500);
        expect(apiErr.errorType).toBe('ServerError');
        expect(apiErr.userMessage).toContain('internal server error');
        expect(apiErr.userMessage).not.toContain('Traceback');
        expect(apiErr.userMessage).not.toContain('RuntimeError');
      }
    });
  });
});
