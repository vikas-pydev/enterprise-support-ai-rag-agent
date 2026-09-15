import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PolicyChatWorkspace } from '@/components/policy/PolicyChatWorkspace';
import { apiClient } from '@/lib/api/client';
import { ApiClientError } from '@/lib/api/errors';
import { mockAskSuccessResponse, mockCitation1 } from '../fixtures/policyFixtures';

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    askPolicyQuestion: vi.fn(),
  },
}));

describe('PolicyChatWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial empty state with title and example questions', () => {
    render(<PolicyChatWorkspace />);

    expect(screen.getByText('Policy Assistant Workspace')).toBeInTheDocument();
    expect(screen.getByText('Ask about company policies')).toBeInTheDocument();
  });

  it('sends question from empty state and renders assistant answer with citations', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.askPolicyQuestion).mockResolvedValueOnce(mockAskSuccessResponse);

    render(<PolicyChatWorkspace />);

    const sampleBtn = screen.getByRole('button', {
      name: /What is the meal per diem allowance for domestic travel\?/i,
    });
    await user.click(sampleBtn);

    // Verify user message appears
    expect(
      screen.getByText('What is the meal per diem allowance for domestic travel?')
    ).toBeInTheDocument();

    // Verify API called
    expect(apiClient.askPolicyQuestion).toHaveBeenCalledWith({
      question: 'What is the meal per diem allowance for domestic travel?',
    });

    // Verify assistant answer appears
    await waitFor(() => {
      expect(
        screen.getByText(
          'The standard domestic meal per diem allowance is $75 per day for all employees.'
        )
      ).toBeInTheDocument();
      expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();
    });
  });

  it('sends question typed by user in composer', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.askPolicyQuestion).mockResolvedValueOnce(mockAskSuccessResponse);

    render(<PolicyChatWorkspace />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'What is the meal allowance?');

    const submitBtn = screen.getByRole('button', { name: /send policy question/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText(
          'The standard domestic meal per diem allowance is $75 per day for all employees.'
        )
      ).toBeInTheDocument();
    });
  });

  it('handles API error safely without crashing, rendering safe error banner', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.askPolicyQuestion).mockRejectedValueOnce(
      new ApiClientError(500, 'DatabaseError', 'Connection refused', 'Database error occurred')
    );

    render(<PolicyChatWorkspace />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'How many PTO days?{Enter}');

    await waitFor(() => {
      expect(
        screen.getByText('I was unable to retrieve policy information due to a service error.')
      ).toBeInTheDocument();
      expect(screen.getByText('Database error occurred')).toBeInTheDocument();
    });
  });

  it('clears conversation when Clear Chat button is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.askPolicyQuestion).mockResolvedValueOnce(mockAskSuccessResponse);

    render(<PolicyChatWorkspace />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'Sample query{Enter}');

    await waitFor(() => {
      expect(screen.getByText('Clear Chat')).toBeInTheDocument();
    });

    const clearBtn = screen.getByRole('button', { name: /clear chat/i });
    await user.click(clearBtn);

    // Empty state should return
    expect(screen.getByText('Ask about company policies')).toBeInTheDocument();
  });
});
