import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ModeSelector } from '@/components/ModeSelector';

describe('ModeSelector', () => {
  it('renders tablist and mode tabs with proper accessibility attributes', () => {
    const handleSelect = vi.fn();
    render(<ModeSelector activeMode="rag" onSelectMode={handleSelect} />);

    expect(screen.getByRole('tablist', { name: /application workspace selector/i })).toBeInTheDocument();

    const policyTab = screen.getByRole('tab', { name: /policy assistant/i });
    const agentTab = screen.getByRole('tab', { name: /enterprise ai agent/i });

    expect(policyTab).toHaveAttribute('aria-selected', 'true');
    expect(agentTab).toHaveAttribute('aria-selected', 'false');
  });

  it('switches to agent mode on tab click', async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    render(<ModeSelector activeMode="rag" onSelectMode={handleSelect} />);

    const agentTab = screen.getByRole('tab', { name: /enterprise ai agent/i });
    await user.click(agentTab);

    expect(handleSelect).toHaveBeenCalledWith('agent');
  });

  it('switches to policy mode on tab click when in agent mode', async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    render(<ModeSelector activeMode="agent" onSelectMode={handleSelect} />);

    const policyTab = screen.getByRole('tab', { name: /policy assistant/i });
    await user.click(policyTab);

    expect(handleSelect).toHaveBeenCalledWith('rag');
  });
});
