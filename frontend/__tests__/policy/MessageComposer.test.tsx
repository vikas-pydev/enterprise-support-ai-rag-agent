import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { MessageComposer } from '@/components/policy/MessageComposer';

describe('MessageComposer', () => {
  it('renders input placeholder and initial submit button disabled', () => {
    const handleSend = vi.fn();
    render(<MessageComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    expect(textarea).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /send policy question/i });
    expect(submitBtn).toBeDisabled();
  });

  it('enables submit button and calls onSendMessage on button click', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<MessageComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'What is the travel policy?');

    const submitBtn = screen.getByRole('button', { name: /send policy question/i });
    expect(submitBtn).not.toBeDisabled();

    await user.click(submitBtn);

    expect(handleSend).toHaveBeenCalledWith('What is the travel policy?');
    expect(textarea).toHaveValue('');
  });

  it('submits on Enter key press without Shift', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<MessageComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'What is the 401k match?{Enter}');

    expect(handleSend).toHaveBeenCalledWith('What is the 401k match?');
    expect(textarea).toHaveValue('');
  });

  it('does not submit on Shift+Enter (allows multiline)', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<MessageComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'Line 1{Shift>}{Enter}{/Shift}Line 2');

    expect(handleSend).not.toHaveBeenCalled();
    expect(textarea).toHaveValue('Line 1\nLine 2');
  });

  it('shows loading stage and disables inputs when isLoading is true', () => {
    const handleSend = vi.fn();
    render(
      <MessageComposer
        onSendMessage={handleSend}
        isLoading={true}
        loadingStage="Searching policies..."
      />
    );

    expect(screen.getByText('Searching policies...')).toBeInTheDocument();
    const textarea = screen.getByPlaceholderText('Awaiting assistant response...');
    expect(textarea).toBeDisabled();

    const submitBtn = screen.getByRole('button', { name: /send policy question/i });
    expect(submitBtn).toBeDisabled();
  });

  it('allows clearing text using the clear input button', async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();
    render(<MessageComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    await user.type(textarea, 'Some text to clear');

    const clearBtn = screen.getByRole('button', { name: /clear input/i });
    expect(clearBtn).toBeInTheDocument();

    await user.click(clearBtn);
    expect(textarea).toHaveValue('');
  });

  it('displays character counter and disables submission when over 1000 characters', async () => {
    const handleSend = vi.fn();
    render(<MessageComposer onSendMessage={handleSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText('Ask a question about internal company policies...');
    const longText = 'a'.repeat(1005);
    fireEvent.change(textarea, { target: { value: longText } });

    expect(screen.getByText('1005/1000')).toBeInTheDocument();
    const submitBtn = screen.getByRole('button', { name: /send policy question/i });
    expect(submitBtn).toBeDisabled();
  });
});
