import { describe, it, expect } from 'vitest';
import {
  HealthResponse,
  AskResponse,
  EmployeeResponse,
  EmployeeLeaveResponse,
  EmployeeTravelResponse,
  AgentChatResponse,
  ApprovalDecisionResponse,
  SessionClearResponse,
} from '@/types/api';
import {
  mockHealthResponse,
  mockAskSuccessResponse,
  mockAskRefusalResponse,
  mockCitation1,
} from '../fixtures/policyFixtures';
import {
  mockEmployeeRecord,
  mockLeaveRecord,
  mockTravelRecord,
  mockAgentSuccessResponse,
  mockAgentApprovalResponse,
  mockApprovalApprovedDecision,
  mockApprovalRejectedDecision,
  mockSessionClearResponse,
} from '../fixtures/agentFixtures';

describe('Frontend Type & API Contracts', () => {
  it('conforms to HealthResponse contract', () => {
    const health: HealthResponse = mockHealthResponse;
    expect(health.status).toBe('healthy');
    expect(typeof health.version).toBe('string');
  });

  it('conforms to AskResponse and CitationSource contracts', () => {
    const askSuccess: AskResponse = mockAskSuccessResponse;
    expect(askSuccess.is_refusal).toBe(false);
    expect(askSuccess.sources.length).toBeGreaterThan(0);

    const citation = askSuccess.sources[0];
    expect(typeof citation.rank).toBe('number');
    expect(typeof citation.rerank_score).toBe('number');
    expect(typeof citation.chunk_uid).toBe('string');
    expect(citation.source_file.endsWith('.md')).toBe(true);

    const askRefusal: AskResponse = mockAskRefusalResponse;
    expect(askRefusal.is_refusal).toBe(true);
    expect(askRefusal.sources).toEqual([]);
  });

  it('conforms to PostgreSQL structured employee data contracts', () => {
    const emp: EmployeeResponse = mockEmployeeRecord;
    expect(emp.employee_id).toBe('E1001');
    expect(emp.manager?.employee_id).toBe('E1000');

    const leave: EmployeeLeaveResponse = mockLeaveRecord;
    expect(leave.total_allocated_days).toBe(25);
    expect(leave.total_remaining_days).toBe(15);
    expect(leave.balances.length).toBe(2);

    const travel: EmployeeTravelResponse = mockTravelRecord;
    expect(travel.total_amount).toBe(1450.0);
    expect(travel.expenses[0].currency).toBe('USD');
  });

  it('conforms to AgentChatResponse and Step contracts', () => {
    const agentResp: AgentChatResponse = mockAgentSuccessResponse;
    expect(agentResp.status).toBe('completed');
    expect(agentResp.steps.length).toBe(2);
    expect(agentResp.steps[0].tool_name).toBe('get_employee_profile_tool');
    expect(agentResp.steps[0].status).toBe('success');
    expect(agentResp.trace?.tools_invoked).toContain('get_employee_profile_tool');

    const approvalResp: AgentChatResponse = mockAgentApprovalResponse;
    expect(approvalResp.status).toBe('pending_approval');
  });

  it('conforms to ApprovalDecisionResponse contract', () => {
    const approved: ApprovalDecisionResponse = mockApprovalApprovedDecision;
    expect(approved.decision).toBe('approve');
    expect(approved.status).toBe('completed');

    const rejected: ApprovalDecisionResponse = mockApprovalRejectedDecision;
    expect(rejected.decision).toBe('reject');
    expect(rejected.status).toBe('rejected');
  });

  it('conforms to SessionClearResponse contract', () => {
    const clearResp: SessionClearResponse = mockSessionClearResponse;
    expect(clearResp.session_id).toBe('session-test-123');
    expect(clearResp.status).toBe('cleared');
  });
});
