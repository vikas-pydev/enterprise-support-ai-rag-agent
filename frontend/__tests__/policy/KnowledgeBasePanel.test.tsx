import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { KnowledgeBasePanel } from '@/components/policy/KnowledgeBasePanel';

describe('KnowledgeBasePanel', () => {
  it('renders indexed policy documents list with search filter', () => {
    const handleSelectDoc = vi.fn();
    render(<KnowledgeBasePanel onSelectDocument={handleSelectDoc} />);

    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
    expect(screen.getByText('Corporate Travel and Expense Policy')).toBeInTheDocument();
    expect(screen.getByText('Employee Leave Policy')).toBeInTheDocument();
    expect(screen.getByText('Employee Benefits and Perks Policy')).toBeInTheDocument();
    expect(screen.getByText('Attendance and Working Hours Policy')).toBeInTheDocument();
  });

  it('filters policy documents based on search query', async () => {
    const user = userEvent.setup();
    const handleSelectDoc = vi.fn();
    render(<KnowledgeBasePanel onSelectDocument={handleSelectDoc} />);

    const searchInput = screen.getByPlaceholderText(/filter indexed policies/i);
    await user.type(searchInput, 'Travel');

    expect(screen.getByText('Corporate Travel and Expense Policy')).toBeInTheDocument();
    expect(screen.queryByText('Attendance and Working Hours Policy')).not.toBeInTheDocument();
  });

  it('triggers onSelectDocument when a document card is clicked', async () => {
    const user = userEvent.setup();
    const handleSelectDoc = vi.fn();
    render(<KnowledgeBasePanel onSelectDocument={handleSelectDoc} />);

    await user.click(screen.getByText('Employee Leave Policy'));
    expect(handleSelectDoc).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'leave_policy',
        title: 'Employee Leave Policy',
      })
    );
  });
});
