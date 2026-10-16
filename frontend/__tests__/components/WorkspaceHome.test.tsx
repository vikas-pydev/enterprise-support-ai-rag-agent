import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { WorkspaceHome } from '@/components/home/WorkspaceHome';

describe('WorkspaceHome', () => {
  it('renders welcome banner, prompt composer, and workspace cards', () => {
    const handleSelectWorkspace = vi.fn();
    render(<WorkspaceHome onSelectWorkspace={handleSelectWorkspace} />);

    expect(screen.getByRole('heading', { name: 'Enterprise Support AI Agent', level: 1 })).toBeInTheDocument();
    expect(screen.getByText('Policy Assistant')).toBeInTheDocument();
    expect(screen.getByText('Enterprise AI Agent')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ask about company policies, employee profiles/i)).toBeInTheDocument();
  });

  it('navigates to policy assistant when Policy card action is clicked', async () => {
    const user = userEvent.setup();
    const handleSelectWorkspace = vi.fn();
    render(<WorkspaceHome onSelectWorkspace={handleSelectWorkspace} />);

    const policyBtn = screen.getByRole('button', { name: /Open Policy Assistant Workspace/i });
    await user.click(policyBtn);

    expect(handleSelectWorkspace).toHaveBeenCalledWith('rag');
  });

  it('navigates to enterprise agent when Agent card action is clicked', async () => {
    const user = userEvent.setup();
    const handleSelectWorkspace = vi.fn();
    render(<WorkspaceHome onSelectWorkspace={handleSelectWorkspace} />);

    const agentBtn = screen.getByRole('button', { name: /Open Enterprise AI Agent Workspace/i });
    await user.click(agentBtn);

    expect(handleSelectWorkspace).toHaveBeenCalledWith('agent');
  });

  it('dispatches employee queries to agent and policy queries to rag via unified composer', async () => {
    const user = userEvent.setup();
    const handleSelectWorkspace = vi.fn();
    render(<WorkspaceHome onSelectWorkspace={handleSelectWorkspace} />);

    const input = screen.getByPlaceholderText(/Ask about company policies, employee profiles/i);
    const submitBtn = screen.getByRole('button', { name: /submit/i });

    // 1. Employee query -> routes to agent
    await user.type(input, 'Who is E1001 manager?');
    await user.click(submitBtn);
    expect(handleSelectWorkspace).toHaveBeenCalledWith('agent', 'Who is E1001 manager?');

    // 2. Policy query -> routes to rag
    await user.clear(input);
    await user.type(input, 'What is the meal per diem?');
    await user.click(submitBtn);
    expect(handleSelectWorkspace).toHaveBeenCalledWith('rag', 'What is the meal per diem?');
  });
});
