import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ToolActivity } from '@/components/agent/ToolActivity';
import { mockStep1, mockStep2 } from '../fixtures/agentFixtures';

describe('ToolActivity', () => {
  it('returns null when steps is empty', () => {
    const { container } = render(<ToolActivity steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders collapsed accordion header and expands on click', async () => {
    const user = userEvent.setup();
    render(<ToolActivity steps={[mockStep1, mockStep2]} />);

    expect(screen.getByText('Tool Activity (2 calls)')).toBeInTheDocument();
    expect(screen.queryByText('get_employee_profile_tool')).not.toBeInTheDocument();

    const accordionBtn = screen.getByRole('button', { name: /tool activity/i });
    await user.click(accordionBtn);

    expect(screen.getByText('get_employee_profile_tool')).toBeInTheDocument();
    expect(screen.getByText('get_employee_travel_tool')).toBeInTheDocument();
    expect(screen.getAllByText('Success').length).toBe(2);
  });

  it('expands single step to reveal input arguments and observation result', async () => {
    const user = userEvent.setup();
    render(<ToolActivity steps={[mockStep1]} />);

    // Expand accordion
    await user.click(screen.getByRole('button', { name: /tool activity/i }));

    // Expand step details
    const stepRow = screen.getByText('get_employee_profile_tool');
    await user.click(stepRow);

    expect(screen.getByText('Input Arguments')).toBeInTheDocument();
    expect(screen.getByText('Observation Result')).toBeInTheDocument();
    expect(screen.getAllByText(/"employee_id": "E1001"/).length).toBeGreaterThan(0);

    // Copy JSON button
    const copyBtn = screen.getByRole('button', { name: /copy json/i });
    const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    await user.click(copyBtn);
    expect(writeTextSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByText('Copied')).toBeInTheDocument();
    });
  });
});
