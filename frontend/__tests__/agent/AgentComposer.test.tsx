import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { AgentComposer } from '@/components/agent/AgentComposer';

describe('AgentComposer', () => {
  it('renders input placeholder and disabled submit button initially', () => {
    const handleSend = vi.fn();
    render(<AgentComposer onSendMessage={handleSend} isLoading={false} />);

    expect(screen.getByPlaceholderText(/Ask the enterprise agent/i)).toBeInTheDocument();
    const submitBtn = screen.getByRole('button', { name: /send query to agent/i });
    expect(submitBtn).toBeDisabled();
  });

  it('submits on button click with trimmed text', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<AgentComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    await user.type(textarea, "Show employee E1001's profile");

    const submitBtn = screen.getByRole('button', { name: /send query to agent/i });
    expect(submitBtn).not.toBeDisabled();
    await user.click(submitBtn);

    expect(handleSend).toHaveBeenCalledWith("Show employee E1001's profile");
    expect(textarea).toHaveValue('');
  });

  it('submits on Enter key without Shift', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<AgentComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    await user.type(textarea, 'Who is E1001 manager?{Enter}');

    expect(handleSend).toHaveBeenCalledWith('Who is E1001 manager?');
    expect(textarea).toHaveValue('');
  });

  it('shows loading indicator and disables input while loading', () => {
    const handleSend = vi.fn();
    render(
      <AgentComposer
        onSendMessage={handleSend}
        isLoading={true}
        loadingStage="Routing domain workers..."
      />
    );

    expect(screen.getByText('Routing domain workers...')).toBeInTheDocument();
    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    expect(textarea).toBeDisabled();

    const submitBtn = screen.getByRole('button', { name: /send query to agent/i });
    expect(submitBtn).toBeDisabled();
    expect(screen.getByText('Executing...')).toBeInTheDocument();
  });

  it('clears input with clear button (X)', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<AgentComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/Ask the enterprise agent/i);
    await user.type(textarea, 'Query to clear');

    const clearBtn = screen.getByRole('button', { name: /clear input/i });
    expect(clearBtn).toBeInTheDocument();

    await user.click(clearBtn);
    expect(textarea).toHaveValue('');
  });
});
