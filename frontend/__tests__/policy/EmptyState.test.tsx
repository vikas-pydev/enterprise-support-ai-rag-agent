import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { EmptyState } from '@/components/policy/EmptyState';

describe('EmptyState', () => {
  it('renders header, description, and suggested question cards', () => {
    const handleSelect = vi.fn();
    render(<EmptyState onSelectQuestion={handleSelect} />);

    expect(screen.getByText('Ask about company policies')).toBeInTheDocument();
    expect(screen.getByText(/What is the meal per diem allowance for domestic travel\?/i)).toBeInTheDocument();
    expect(screen.getByText(/How much does the company match 401\(k\) contributions\?/i)).toBeInTheDocument();
    expect(screen.getByText(/What are the core collaboration hours for remote employees\?/i)).toBeInTheDocument();
    expect(screen.getByText(/What is the company pet insurance reimbursement policy\?/i)).toBeInTheDocument();
  });

  it('triggers onSelectQuestion when a question button is clicked', async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    render(<EmptyState onSelectQuestion={handleSelect} />);

    const questionBtn = screen.getByRole('button', {
      name: /What is the meal per diem allowance for domestic travel\?/i,
    });
    await user.click(questionBtn);

    expect(handleSelect).toHaveBeenCalledWith(
      'What is the meal per diem allowance for domestic travel?'
    );
  });

  it('disables buttons when disabled prop is true', () => {
    const handleSelect = vi.fn();
    render(<EmptyState onSelectQuestion={handleSelect} disabled={true} />);

    const questionBtn = screen.getByRole('button', {
      name: /What is the meal per diem allowance for domestic travel\?/i,
    });
    expect(questionBtn).toBeDisabled();
  });
});
