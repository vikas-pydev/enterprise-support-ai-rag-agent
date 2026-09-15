import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { AgentEmptyState } from '@/components/agent/AgentEmptyState';

describe('AgentEmptyState', () => {
  it('renders title, description, and technical demo prompt cards', () => {
    const handleSelect = vi.fn();
    render(<AgentEmptyState onSelectPrompt={handleSelect} />);

    expect(screen.getByText('Enterprise AI Agent Workspace')).toBeInTheDocument();
    expect(screen.getByText('Employee Profile')).toBeInTheDocument();
    expect(screen.getByText('Leave Balances')).toBeInTheDocument();
    expect(screen.getByText('Travel & Expenses')).toBeInTheDocument();
    expect(screen.getByText('Human-in-the-Loop Gate')).toBeInTheDocument();
  });

  it('triggers onSelectPrompt when a demo query card is clicked', async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    render(<AgentEmptyState onSelectPrompt={handleSelect} />);

    const card = screen.getByRole('button', { name: /Show employee E1001's information/i });
    await user.click(card);

    expect(handleSelect).toHaveBeenCalledWith("Show employee E1001's information.");
  });

  it('disables all prompt cards when disabled is true', () => {
    const handleSelect = vi.fn();
    render(<AgentEmptyState onSelectPrompt={handleSelect} disabled={true} />);

    const card = screen.getByRole('button', { name: /Show employee E1001's information/i });
    expect(card).toBeDisabled();
  });
});
