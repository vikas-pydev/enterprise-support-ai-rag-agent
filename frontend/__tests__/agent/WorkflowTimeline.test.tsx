import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { WorkflowTimeline } from '@/components/agent/WorkflowTimeline';
import { mockStep1, mockStep2 } from '../fixtures/agentFixtures';

describe('WorkflowTimeline', () => {
  it('returns null when steps is empty and approval is not pending', () => {
    const { container } = render(<WorkflowTimeline steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders complete workflow nodes for multi-step agent execution', () => {
    render(<WorkflowTimeline steps={[mockStep1, mockStep2]} status="completed" />);

    expect(screen.getByText('Multi-Agent Execution Workflow')).toBeInTheDocument();
    expect(screen.getByText('2 tool calls executed')).toBeInTheDocument();

    // Node 1: Supervisor
    expect(screen.getAllByText('Supervisor Router').length).toBeGreaterThan(0);

    // Node 2 & 3: Workers
    expect(screen.getAllByText('Employee Records').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Travel & Expense').length).toBeGreaterThan(0);

    // Node 4: Synthesis
    expect(screen.getAllByText('Final Synthesis').length).toBeGreaterThan(0);
  });

  it('renders Human Authorization node when isApprovalPending is true', () => {
    render(<WorkflowTimeline steps={[]} isApprovalPending={true} status="pending_approval" />);

    expect(screen.getAllByText('Human Authorization').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Awaiting operator approval').length).toBeGreaterThan(0);
  });
});
