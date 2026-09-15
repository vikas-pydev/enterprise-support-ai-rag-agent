import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AgentChatWorkspace } from '@/components/agent/AgentChatWorkspace';
import { apiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import {
  mockAgentSuccessResponse,
  mockAgentApprovalResponse,
  mockApprovalApprovedDecision,
  mockSessionClearResponse,
} from '../fixtures/agentFixtures';

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    agentChat: vi.fn(),
    clearSession: vi.fn(),
    deleteSession: vi.fn(),
    submitApprovalDecision: vi.fn(),
  },
}));

describe('AgentChatWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial workspace with empty state and session control bar', () => {
    render(<AgentChatWorkspace />);

    expect(screen.getAllByText('Enterprise AI Agent Workspace').length).toBeGreaterThan(0);
    expect(screen.getByText('Employee Profile')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new session/i })).toBeInTheDocument();
  });

  it('sends prompt from demo query and renders multi-step agent answer', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.agentChat).mockResolvedValueOnce(mockAgentSuccessResponse);

    render(<AgentChatWorkspace />);

    const demoBtn = screen.getByRole('button', { name: /Show employee E1001's information/i });
    await user.click(demoBtn);

    expect(apiClient.agentChat).toHaveBeenCalledWith({
      session_id: expect.stringMatching(/^session-agent-/),
      message: "Show employee E1001's information.",
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          'Alice Johnson (E1001) has spent $1,450.00 on approved travel claims. Her manager is Robert Vance (VP of Engineering).'
        )
      ).toBeInTheDocument();
      expect(screen.getByText('Multi-Agent Execution Workflow')).toBeInTheDocument();
    });
  });

  it('handles HITL approval flow: renders ApprovalCard and submits decision', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.agentChat).mockResolvedValueOnce(mockAgentApprovalResponse);
    vi.mocked(apiClient.submitApprovalDecision).mockResolvedValueOnce(mockApprovalApprovedDecision);

    render(<AgentChatWorkspace />);

    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    await user.type(textarea, 'Show confidential compensation for E1000.{Enter}');

    // Verify approval card appears
    await waitFor(() => {
      expect(screen.getByText('Human Approval Required')).toBeInTheDocument();
      expect(screen.getByText('appr_req_789')).toBeInTheDocument();
    });

    // Operator clicks Approve
    const approveBtn = screen.getByRole('button', { name: /approve & continue/i });
    await user.click(approveBtn);

    expect(apiClient.submitApprovalDecision).toHaveBeenCalledWith('appr_req_789', {
      decision: 'approve',
      notes: undefined,
    });

    // Verification that message content was updated with authorized output
    await waitFor(() => {
      expect(
        screen.getByText(/Compensation records authorized: Base salary and bonus details/i)
      ).toBeInTheDocument();
      expect(screen.getByText('Operation authorized! Resumed workflow and received response.')).toBeInTheDocument();
    });
  });

  it('clears session history on backend and frontend', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.agentChat).mockResolvedValueOnce(mockAgentSuccessResponse);
    vi.mocked(apiClient.clearSession).mockResolvedValueOnce(mockSessionClearResponse);

    render(<AgentChatWorkspace />);

    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    await user.type(textarea, 'Query 1{Enter}');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /clear history/i })).toBeInTheDocument();
    });

    // Click twice for confirmation
    await user.click(screen.getByRole('button', { name: /clear history/i }));
    await user.click(screen.getByRole('button', { name: /confirm clear\?/i }));

    expect(apiClient.clearSession).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByText(/cleared successfully on backend and frontend/i)).toBeInTheDocument();
    });
  });

  it('deletes session on backend and resets session ID', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.deleteSession).mockResolvedValueOnce({
      session_id: 'session-old',
      status: 'deleted',
      message: 'Deleted',
    });

    render(<AgentChatWorkspace />);

    const deleteBtn = screen.getByRole('button', { name: /delete/i });
    await user.click(deleteBtn);
    await user.click(screen.getByRole('button', { name: /confirm delete\?/i }));

    expect(apiClient.deleteSession).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByText(/deleted from backend storage/i)).toBeInTheDocument();
    });
  });

  it('handles agent API failure with safe error message', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.agentChat).mockRejectedValueOnce(
      new ApiClientError(500, 'ServerError', 'Crash in supervisor', 'Internal server error')
    );

    render(<AgentChatWorkspace />);

    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    await user.type(textarea, 'Broken query{Enter}');

    await waitFor(() => {
      expect(
        screen.getByText('The enterprise agent encountered an error processing your inquiry.')
      ).toBeInTheDocument();
      expect(screen.getByText('Internal server error')).toBeInTheDocument();
    });
  });
});
