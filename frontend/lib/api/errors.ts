/**
 * Standardized API Error Handling for the Next.js Frontend.
 *
 * Guarantees that internal exception dumps, database connection strings,
 * stack traces, and sensitive backend implementation details are never
 * exposed in user-facing error messages.
 */

import { ApiErrorResponse } from '@/types/api';

export class ApiClientError extends Error {
  public readonly statusCode: number;
  public readonly errorType: string;
  public readonly detail: string;
  public readonly userMessage: string;

  constructor(
    statusCode: number,
    errorType: string,
    detail: string,
    userMessage: string
  ) {
    super(userMessage);
    this.name = 'ApiClientError';
    this.statusCode = statusCode;
    this.errorType = errorType;
    this.detail = detail;
    this.userMessage = userMessage;

    // Maintains proper stack trace for where error was thrown (V8 only)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiClientError);
    }
  }

  /**
   * Translates HTTP status codes and backend error types into safe, clean user-facing messages.
   */
  public static create(
    statusCode: number,
    payload?: ApiErrorResponse | Record<string, unknown> | string
  ): ApiClientError {
    let errorType = 'UnknownError';
    let detail = '';

    if (typeof payload === 'string') {
      detail = payload;
    } else if (payload && typeof payload === 'object') {
      if ('error_type' in payload && typeof payload.error_type === 'string') {
        errorType = payload.error_type;
      }
      if ('detail' in payload) {
        if (typeof payload.detail === 'string') {
          detail = payload.detail;
        } else if (Array.isArray(payload.detail)) {
          // FastAPI 422 validation errors
          detail = payload.detail
            .map((err) => (typeof err === 'object' && err?.msg ? err.msg : JSON.stringify(err)))
            .join(', ');
          errorType = 'ValidationError';
        } else {
          detail = JSON.stringify(payload.detail);
        }
      }
    }

    // Determine sanitized user message
    let userMessage = 'An unexpected error occurred. Please try again.';

    if (statusCode === 0 || statusCode === 503) {
      errorType = 'ServiceUnavailable';
      userMessage = 'The enterprise AI backend service is currently unreachable. Please verify the backend is running.';
    } else if (statusCode === 403) {
      errorType = errorType === 'UnknownError' ? 'AuthorizationError' : errorType;
      userMessage = detail && !detail.includes('Traceback')
        ? detail
        : 'You do not have permission to perform this action or access this session.';
    } else if (statusCode === 404) {
      errorType = errorType === 'UnknownError' ? 'NotFoundError' : errorType;
      userMessage = detail && !detail.includes('Traceback')
        ? detail
        : 'The requested resource or employee record was not found.';
    } else if (statusCode === 400 || statusCode === 422) {
      errorType = 'ValidationError';
      userMessage = detail && !detail.includes('Traceback')
        ? `Invalid request: ${detail}`
        : 'The submitted request contained invalid or incomplete parameters.';
    } else if (statusCode === 500) {
      if (errorType === 'DatabaseError' || detail.toLowerCase().includes('database')) {
        errorType = 'DatabaseError';
        userMessage = 'A database error occurred while processing your request. Please try again later.';
      } else {
        errorType = 'ServerError';
        userMessage = 'An internal server error occurred while processing your request.';
      }
    } else if (statusCode === 408 || errorType === 'TimeoutError') {
      errorType = 'TimeoutError';
      userMessage = 'The request timed out waiting for the AI backend. Please try again.';
    }

    return new ApiClientError(statusCode, errorType, detail, userMessage);
  }
}
