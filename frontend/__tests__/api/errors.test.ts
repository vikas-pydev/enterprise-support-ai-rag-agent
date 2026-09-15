import { describe, it, expect } from 'vitest';
import { ApiClientError } from '@/lib/api/errors';

describe('ApiClientError', () => {
  it('instantiates correctly with direct properties', () => {
    const error = new ApiClientError(404, 'NotFoundError', 'Record missing', 'Not found');
    expect(error.statusCode).toBe(404);
    expect(error.errorType).toBe('NotFoundError');
    expect(error.detail).toBe('Record missing');
    expect(error.userMessage).toBe('Not found');
    expect(error.name).toBe('ApiClientError');
  });

  describe('ApiClientError.create factory method', () => {
    it('creates ServiceUnavailable error for statusCode 0 (network failure)', () => {
      const err = ApiClientError.create(0, 'Failed to fetch');
      expect(err.statusCode).toBe(0);
      expect(err.errorType).toBe('ServiceUnavailable');
      expect(err.userMessage).toContain('backend service is currently unreachable');
    });

    it('creates ServiceUnavailable error for statusCode 503', () => {
      const err = ApiClientError.create(503, { detail: 'Service shutting down' });
      expect(err.statusCode).toBe(503);
      expect(err.errorType).toBe('ServiceUnavailable');
      expect(err.userMessage).toContain('backend service is currently unreachable');
    });

    it('creates NotFoundError for statusCode 404 with safe detail', () => {
      const err = ApiClientError.create(404, { detail: 'Employee E999 not found', error_type: 'NotFoundError' });
      expect(err.statusCode).toBe(404);
      expect(err.errorType).toBe('NotFoundError');
      expect(err.userMessage).toBe('Employee E999 not found');
    });

    it('strips Traceback from 404 detail and provides safe user message', () => {
      const err = ApiClientError.create(404, { detail: 'Traceback (most recent call last)...' });
      expect(err.statusCode).toBe(404);
      expect(err.userMessage).toBe('The requested resource or employee record was not found.');
    });

    it('creates ValidationError for 400 and 422 with string detail', () => {
      const err = ApiClientError.create(400, { detail: 'Missing question field', error_type: 'ValidationError' });
      expect(err.statusCode).toBe(400);
      expect(err.errorType).toBe('ValidationError');
      expect(err.userMessage).toBe('Invalid request: Missing question field');
    });

    it('formats FastAPI validation error array in detail', () => {
      const err = ApiClientError.create(422, {
        detail: [
          { msg: 'Field "session_id" is required' },
          { msg: 'Field "message" cannot be empty' },
        ],
      });
      expect(err.statusCode).toBe(422);
      expect(err.errorType).toBe('ValidationError');
      expect(err.detail).toBe('Field "session_id" is required, Field "message" cannot be empty');
      expect(err.userMessage).toBe(
        'Invalid request: Field "session_id" is required, Field "message" cannot be empty'
      );
    });

    it('creates DatabaseError for 500 when error_type is DatabaseError or detail contains database', () => {
      const err1 = ApiClientError.create(500, {
        detail: 'PostgreSQL connection failed at localhost:5432',
        error_type: 'DatabaseError',
      });
      expect(err1.statusCode).toBe(500);
      expect(err1.errorType).toBe('DatabaseError');
      expect(err1.userMessage).toBe(
        'A database error occurred while processing your request. Please try again later.'
      );

      const err2 = ApiClientError.create(500, {
        detail: 'database pool timeout',
      });
      expect(err2.errorType).toBe('DatabaseError');
    });

    it('creates ServerError for generic 500 without database keywords', () => {
      const err = ApiClientError.create(500, { detail: 'Unhandled NullPointer' });
      expect(err.statusCode).toBe(500);
      expect(err.errorType).toBe('ServerError');
      expect(err.userMessage).toBe(
        'An internal server error occurred while processing your request.'
      );
    });

    it('creates TimeoutError for statusCode 408', () => {
      const err = ApiClientError.create(408);
      expect(err.statusCode).toBe(408);
      expect(err.errorType).toBe('TimeoutError');
      expect(err.userMessage).toContain('timed out');
    });

    it('handles string payload directly', () => {
      const err = ApiClientError.create(500, 'Raw string error');
      expect(err.detail).toBe('Raw string error');
    });
  });
});
