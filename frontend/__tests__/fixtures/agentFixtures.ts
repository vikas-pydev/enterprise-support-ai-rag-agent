import {
  AgentChatResponse,
  AgentStepResponse,
  ApprovalDecisionResponse,
  EmployeeResponse,
  EmployeeLeaveResponse,
  EmployeeTravelResponse,
  SessionClearResponse,
} from '@/types/api';
import { mockCitation1 } from './policyFixtures';

export const mockEmployeeRecord: EmployeeResponse = {
  employee_id: 'E1001',
  name: 'Alice Johnson',
  email: 'alice.johnson@enterprise.com',
  department: 'Engineering',
  job_title: 'Senior Staff Engineer',
  created_at: '2023-01-15T09:00:00Z',
  manager: {
    employee_id: 'E1000',
    name: 'Robert Vance',
    email: 'robert.vance@enterprise.com',
    job_title: 'VP of Engineering',
  },
};

export const mockLeaveRecord: EmployeeLeaveResponse = {
  employee_id: 'E1001',
  name: 'Alice Johnson',
  department: 'Engineering',
  total_allocated_days: 25,
  total_used_days: 10,
  total_remaining_days: 15,
  balances: [
    {
      leave_type: 'Annual',
      total_days: 20,
      used_days: 8,
      remaining_days: 12,
      updated_at: '2024-03-01T10:00:00Z',
    },
    {
      leave_type: 'Sick',
      total_days: 5,
      used_days: 2,
      remaining_days: 3,
      updated_at: '2024-03-01T10:00:00Z',
    },
  ],
};

export const mockTravelRecord: EmployeeTravelResponse = {
  employee_id: 'E1001',
  name: 'Alice Johnson',
  department: 'Engineering',
  total_claims: 2,
  total_amount: 1450.0,
  approved_amount: 1450.0,
  submitted_amount: 0.0,
  reimbursed_amount: 1450.0,
  by_category: {
    Flight: 950.0,
    Hotel: 500.0,
  },
  expenses: [
    {
      id: 101,
      expense_date: '2024-02-10',
      category: 'Flight',
      amount: 950.0,
      currency: 'USD',
      status: 'APPROVED',
      description: 'Flight to Tech Conference 2024',
      created_at: '2024-02-12T14:30:00Z',
    },
  ],
};

export const mockStep1: AgentStepResponse = {
  step_number: 1,
  tool_name: 'get_employee_profile_tool',
  tool_args: { employee_id: 'E1001' },
  tool_result: {
    employee_id: 'E1001',
    name: 'Alice Johnson',
    department: 'Engineering',
    manager_name: 'Robert Vance',
  },
  status: 'success',
  duration_ms: 120,
  error: null,
};

export const mockStep2: AgentStepResponse = {
  step_number: 2,
  tool_name: 'get_employee_travel_tool',
  tool_args: { employee_id: 'E1001' },
  tool_result: {
    total_spent: 1450.0,
    claims_count: 2,
  },
  status: 'success',
  duration_ms: 85,
  error: null,
};

export const mockAgentSuccessResponse: AgentChatResponse = {
  session_id: 'session-test-123',
  query: 'How much has E1001 spent on travel and who is their manager?',
  answer: 'Alice Johnson (E1001) has spent $1,450.00 on approved travel claims. Her manager is Robert Vance (VP of Engineering).',
  status: 'completed',
  steps: [mockStep1, mockStep2],
  total_steps: 2,
  duration_ms: 850,
  used_rag: false,
  citations: [],
  trace: {
    session_id: 'session-test-123',
    total_steps: 2,
    total_duration_ms: 850,
    used_rag: false,
    status: 'completed',
    tools_invoked: ['get_employee_profile_tool', 'get_employee_travel_tool'],
  },
};

export const mockAgentApprovalResponse: AgentChatResponse = {
  session_id: 'session-test-456',
  query: 'Show confidential compensation for E1000.',
  answer: "Approval Request ID: 'appr_req_789'. Reason: Sensitive executive compensation lookup requires operator approval.",
  status: 'pending_approval',
  steps: [],
  total_steps: 0,
  duration_ms: 320,
  used_rag: false,
  citations: [],
  trace: {
    session_id: 'session-test-456',
    total_steps: 0,
    total_duration_ms: 320,
    used_rag: false,
    status: 'pending_approval',
    tools_invoked: [],
  },
};

export const mockApprovalApprovedDecision: ApprovalDecisionResponse = {
  approval_id: 'appr_req_789',
  decision: 'approve',
  status: 'completed',
  answer: 'Compensation records authorized: Base salary and bonus details for E1000 retrieved.',
  duration_ms: 640,
  trace: {
    total_steps: 1,
    total_duration_ms: 640,
    used_rag: false,
    status: 'completed',
    tools_invoked: ['get_salary_records_tool'],
  },
};

export const mockApprovalRejectedDecision: ApprovalDecisionResponse = {
  approval_id: 'appr_req_789',
  decision: 'reject',
  status: 'rejected',
  answer: 'The request to view confidential compensation was rejected by the operator.',
  duration_ms: 110,
  trace: {
    total_steps: 0,
    total_duration_ms: 110,
    used_rag: false,
    status: 'rejected',
    tools_invoked: [],
  },
};

export const mockSessionClearResponse: SessionClearResponse = {
  session_id: 'session-test-123',
  status: 'cleared',
  message: "Session 'session-test-123' memory cleared successfully.",
};
