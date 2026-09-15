import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { AgentMessage } from '@/components/agent/AgentMessage';
import { AgentChatMessage } from '@/types/agent';
import { mockStep1, mockStep2 } from '../fixtures/agentFixtures';
import { mockCitation1 } from '../fixtures/policyFixtures';

describe('AgentMessage', () => {
  it('renders user message', () => {
    const userMsg: AgentChatMessage = {
      id: 'agent-msg-1',
      role: 'user',
      content: 'Show travel for E1001',
      timestamp: new Date('2024-03-10T14:00:00Z'),
    };

    render(<AgentMessage message={userMsg} onApprovalDecision={vi.fn()} />);
    expect(screen.getByText('You')).toBeInTheDocument();
    expect(screen.getByText('Show travel for E1001')).toBeInTheDocument();
  });

  it('renders assistant message with workflow, tool activity, citations, and execution summary', async () => {
    const user = userEvent.setup();
    const assistantMsg: AgentChatMessage = {
      id: 'agent-msg-2',
      role: 'assistant',
      content: 'Alice Johnson has spent $1,450 on travel.',
      timestamp: new Date('2024-03-10T14:01:00Z'),
      sessionId: 'session-1234567890abcdef',
      status: 'completed',
      steps: [mockStep1, mockStep2],
      totalSteps: 2,
      durationMs: 850,
      usedRag: true,
      citations: [mockCitation1],
    };

    render(<AgentMessage message={assistantMsg} onApprovalDecision={vi.fn()} />);

    expect(screen.getByText('Enterprise AI Agent')).toBeInTheDocument();
    expect(screen.getByText('LangGraph Multi-Agent')).toBeInTheDocument();
    expect(screen.getByText('Alice Johnson has spent $1,450 on travel.')).toBeInTheDocument();

    // Workflow timeline & tool activity
    expect(screen.getByText('Multi-Agent Execution Workflow')).toBeInTheDocument();
    expect(screen.getByText('Tool Activity (2 calls)')).toBeInTheDocument();

    // Citations
    expect(screen.getByText(/Retrieved Policy Knowledge & Citations/i)).toBeInTheDocument();
    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();

    // Execution summary
    expect(screen.getByText('Execution Summary:')).toBeInTheDocument();

    // Copy button
    const copyBtn = screen.getByRole('button', { name: /copy agent answer/i });
    const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    await user.click(copyBtn);
    expect(writeTextSpy).toHaveBeenCalledWith('Alice Johnson has spent $1,450 on travel.');
  });

  it('renders approval card when approvalId is present', () => {
    const approvalMsg: AgentChatMessage = {
      id: 'agent-msg-3',
      role: 'assistant',
      content: 'Approval required for sensitive operation.',
      timestamp: new Date(),
      status: 'pending_approval',
      approvalId: 'appr_req_999',
      approvalStatus: 'pending',
      approvalReason: 'Requires HR manager sign-off',
      targetWorker: 'Employee Records',
    };

    render(<AgentMessage message={approvalMsg} onApprovalDecision={vi.fn()} />);

    expect(screen.getByText('Human Approval Required')).toBeInTheDocument();
    expect(screen.getByText('Requires HR manager sign-off')).toBeInTheDocument();
  });
});
