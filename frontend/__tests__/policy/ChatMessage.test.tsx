import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ChatMessage } from '@/components/policy/ChatMessage';
import { PolicyChatMessage } from '@/types/chat';
import { mockCitation1 } from '../fixtures/policyFixtures';

describe('ChatMessage (Policy)', () => {
  it('renders user message correctly', () => {
    const userMsg: PolicyChatMessage = {
      id: 'msg-1',
      role: 'user',
      content: 'What is the travel policy?',
      timestamp: new Date('2024-03-10T12:00:00Z'),
    };

    render(<ChatMessage message={userMsg} />);
    expect(screen.getByText('You')).toBeInTheDocument();
    expect(screen.getByText('What is the travel policy?')).toBeInTheDocument();
  });

  it('renders grounded assistant response with citations and copy button', async () => {
    const user = userEvent.setup();
    const assistantMsg: PolicyChatMessage = {
      id: 'msg-2',
      role: 'assistant',
      content: 'The meal allowance is $75/day.',
      timestamp: new Date('2024-03-10T12:01:00Z'),
      sources: [mockCitation1],
      isRefusal: false,
    };

    render(<ChatMessage message={assistantMsg} />);
    expect(screen.getByText('Policy Assistant')).toBeInTheDocument();
    expect(screen.getByText('The meal allowance is $75/day.')).toBeInTheDocument();
    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();

    const copyBtn = screen.getByRole('button', { name: /copy answer/i });
    const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    await user.click(copyBtn);
    expect(writeTextSpy).toHaveBeenCalledWith('The meal allowance is $75/day.');
    await waitFor(() => {
      expect(screen.getByText('Copied')).toBeInTheDocument();
    });
  });

  it('renders refusal banner when isRefusal is true', () => {
    const refusalMsg: PolicyChatMessage = {
      id: 'msg-3',
      role: 'assistant',
      content: 'I could not find documented facts for this inquiry.',
      timestamp: new Date(),
      isRefusal: true,
      sources: [],
    };

    render(<ChatMessage message={refusalMsg} />);
    expect(screen.getByText('Knowledge Base Refusal')).toBeInTheDocument();
    expect(screen.getByText(/Insufficient supporting evidence was retrieved/i)).toBeInTheDocument();
  });

  it('renders error banner when error is present', () => {
    const errorMsg: PolicyChatMessage = {
      id: 'msg-4',
      role: 'assistant',
      content: 'I was unable to retrieve policy information.',
      timestamp: new Date(),
      error: 'Backend connection timeout after 5000ms',
    };

    render(<ChatMessage message={errorMsg} />);
    expect(screen.getByText('Service Error')).toBeInTheDocument();
    expect(screen.getByText('Backend connection timeout after 5000ms')).toBeInTheDocument();
  });
});
