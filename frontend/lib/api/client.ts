/**
 * Typed API client for FastAPI backend communication.
 * Connects Next.js frontend to the Enterprise Support AI Agent REST APIs.
 */

import {
  HealthResponse,
  AskRequest,
  AskResponse,
  EmployeeResponse,
  EmployeeLeaveResponse,
  EmployeeTravelResponse,
  AgentChatRequest,
  AgentChatResponse,
  SessionClearResponse,
  ApprovalDecisionRequest,
  ApprovalDecisionResponse,
  ApiErrorResponse,
} from '@/types/api';
import { ApiClientError } from './errors';

export class EnterpriseApiClient {
  private baseUrl: string;
  private defaultTimeoutMs: number;

  constructor(
    baseUrl: string = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000',
    defaultTimeoutMs: number = 45000
  ) {
    // Remove trailing slash if provided
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public setBaseUrl(url: string): void {
    this.baseUrl = url.replace(/\/+$/, '');
  }

  /**
   * Internal generic fetch wrapper with timeout and standardized error handling.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = this.defaultTimeoutMs
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...(options.headers || {}),
        },
      });

      clearTimeout(timeoutId);

      // Handle successful responses
      if (response.ok) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          return (await response.json()) as T;
        }
        return (await response.text()) as unknown as T;
      }

      // Parse error payload if JSON
      let errorPayload: ApiErrorResponse | Record<string, unknown> | string = '';
      try {
        errorPayload = await response.json();
      } catch {
        try {
          errorPayload = await response.text();
        } catch {
          errorPayload = response.statusText;
        }
      }

      throw ApiClientError.create(response.status, errorPayload);
    } catch (err: unknown) {
      clearTimeout(timeoutId);

      if (err instanceof ApiClientError) {
        throw err;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new ApiClientError(
          408,
          'TimeoutError',
          `Request to ${endpoint} timed out after ${timeoutMs}ms.`,
          'The request took too long to complete. Please try again.'
        );
      }

      // Network connection failures (e.g. backend offline / connection refused)
      const message = err instanceof Error ? err.message : String(err);
      throw ApiClientError.create(0, message);
    }
  }

  // =====================================================================
  // 1. HEALTH ENDPOINT (GET /health)
  // =====================================================================
  public async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health', {
      method: 'GET',
      cache: 'no-store',
    }, 5000);
  }

  // =====================================================================
  // 2. POLICY ASSISTANT (POST /api/v1/ask)
  // =====================================================================
  public async askPolicyQuestion(req: AskRequest): Promise<AskResponse> {
    return this.request<AskResponse>('/api/v1/ask', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  // =====================================================================
  // 3. STRUCTURED OPERATIONAL DATA (GET /api/v1/employees/...)
  // =====================================================================
  public async getEmployee(employeeId: string): Promise<EmployeeResponse> {
    const cleanId = encodeURIComponent(employeeId.trim());
    return this.request<EmployeeResponse>(`/api/v1/employees/${cleanId}`, {
      method: 'GET',
    });
  }

  public async getEmployeeLeave(employeeId: string): Promise<EmployeeLeaveResponse> {
    const cleanId = encodeURIComponent(employeeId.trim());
    return this.request<EmployeeLeaveResponse>(`/api/v1/employees/${cleanId}/leave`, {
      method: 'GET',
    });
  }

  public async getEmployeeTravel(employeeId: string): Promise<EmployeeTravelResponse> {
    const cleanId = encodeURIComponent(employeeId.trim());
    return this.request<EmployeeTravelResponse>(`/api/v1/employees/${cleanId}/travel`, {
      method: 'GET',
    });
  }

  // =====================================================================
  // 4. CONVERSATIONAL AGENT (POST /api/v1/agent/chat)
  // =====================================================================
  public async agentChat(req: AgentChatRequest): Promise<AgentChatResponse> {
    return this.request<AgentChatResponse>('/api/v1/agent/chat', {
      method: 'POST',
      body: JSON.stringify(req),
    }, 60000); // Allow up to 60s for multi-step agent reasoning
  }

  public async clearSession(sessionId: string): Promise<SessionClearResponse> {
    const cleanId = encodeURIComponent(sessionId.trim());
    return this.request<SessionClearResponse>(`/api/v1/agent/sessions/${cleanId}/clear`, {
      method: 'POST',
    });
  }

  public async deleteSession(sessionId: string): Promise<SessionClearResponse> {
    const cleanId = encodeURIComponent(sessionId.trim());
    return this.request<SessionClearResponse>(`/api/v1/agent/sessions/${cleanId}`, {
      method: 'DELETE',
    });
  }

  // =====================================================================
  // 5. HUMAN-IN-THE-LOOP APPROVAL (POST /api/v1/agent/approvals/{id})
  // =====================================================================
  public async submitApprovalDecision(
    approvalId: string,
    req: ApprovalDecisionRequest
  ): Promise<ApprovalDecisionResponse> {
    const cleanId = encodeURIComponent(approvalId.trim());
    return this.request<ApprovalDecisionResponse>(`/api/v1/agent/approvals/${cleanId}`, {
      method: 'POST',
      body: JSON.stringify(req),
    }, 60000);
  }
}

// Singleton export
export const apiClient = new EnterpriseApiClient();
