import { AgentStepResponse, AgentExecutionTraceResponse, CitationSource } from './api';

export type AgentMessageRole = 'user' | 'assistant';

export type AgentWorkflowStatus =
  | 'completed'
  | 'in_progress'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'max_steps_reached'
  | 'clarification_needed'
  | 'error'
  | string;

export interface AgentChatMessage {
  id: string;
  role: AgentMessageRole;
  content: string;
  timestamp: Date;
  sessionId?: string;
  status?: AgentWorkflowStatus;
  steps?: AgentStepResponse[];
  totalSteps?: number;
  durationMs?: number;
  usedRag?: boolean;
  citations?: CitationSource[];
  trace?: AgentExecutionTraceResponse | null;
  error?: string | null;
  // Human-in-the-Loop fields
  approvalId?: string | null;
  approvalRequired?: boolean;
  approvalStatus?: 'pending' | 'approved' | 'rejected' | 'completed' | 'error' | string;
  approvalReason?: string | null;
  approvalDecision?: 'approve' | 'reject' | string;
  approvalNotes?: string | null;
  targetWorker?: string | null;
}
