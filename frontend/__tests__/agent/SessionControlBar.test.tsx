import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SessionControlBar } from '@/components/agent/SessionControlBar';

describe('SessionControlBar', () => {
  it('renders session ID, message turn count, and action buttons', () => {
    render(
      <SessionControlBar
        sessionId="session-xyz-123"
        onNewSession={vi.fn()}
        onClearSession={vi.fn()}
        onDeleteSession={vi.fn()}
        isLoading={false}
        messageCount={4}
      />
    );

    expect(screen.getByText('session-xyz-123')).toBeInTheDocument();
    expect(screen.getByText('4 turns')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new session/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear history/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('copies session ID to clipboard when copy button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <SessionControlBar
        sessionId="session-xyz-123"
        onNewSession={vi.fn()}
        onClearSession={vi.fn()}
        onDeleteSession={vi.fn()}
        isLoading={false}
        messageCount={0}
      />
    );

    const copyBtn = screen.getByRole('button', { name: /copy session id/i });
    const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    await user.click(copyBtn);

    expect(writeTextSpy).toHaveBeenCalledWith('session-xyz-123');
  });

  it('calls onNewSession when New Session clicked', async () => {
    const user = userEvent.setup();
    const handleNew = vi.fn();
    render(
      <SessionControlBar
        sessionId="session-xyz-123"
        onNewSession={handleNew}
        onClearSession={vi.fn()}
        onDeleteSession={vi.fn()}
        isLoading={false}
        messageCount={0}
      />
    );

    await user.click(screen.getByRole('button', { name: /new session/i }));
    expect(handleNew).toHaveBeenCalledTimes(1);
  });

  it('requires two clicks to confirm clearing session history', async () => {
    const user = userEvent.setup();
    const handleClear = vi.fn();
    render(
      <SessionControlBar
        sessionId="session-xyz-123"
        onNewSession={vi.fn()}
        onClearSession={handleClear}
        onDeleteSession={vi.fn()}
        isLoading={false}
        messageCount={2}
      />
    );

    const clearBtn = screen.getByRole('button', { name: /clear history/i });
    // First click: prompts confirmation
    await user.click(clearBtn);
    expect(handleClear).not.toHaveBeenCalled();
    expect(screen.getByText('Confirm Clear?')).toBeInTheDocument();

    // Second click: executes clear
    await user.click(screen.getByRole('button', { name: /confirm clear\?/i }));
    expect(handleClear).toHaveBeenCalledTimes(1);
  });

  it('requires two clicks to confirm deleting session', async () => {
    const user = userEvent.setup();
    const handleDelete = vi.fn();
    render(
      <SessionControlBar
        sessionId="session-xyz-123"
        onNewSession={vi.fn()}
        onClearSession={vi.fn()}
        onDeleteSession={handleDelete}
        isLoading={false}
        messageCount={0}
      />
    );

    const deleteBtn = screen.getByRole('button', { name: /delete/i });
    // First click: prompts confirmation
    await user.click(deleteBtn);
    expect(handleDelete).not.toHaveBeenCalled();
    expect(screen.getByText('Confirm Delete?')).toBeInTheDocument();

    // Second click: executes delete
    await user.click(screen.getByRole('button', { name: /confirm delete\?/i }));
    expect(handleDelete).toHaveBeenCalledTimes(1);
  });
});
