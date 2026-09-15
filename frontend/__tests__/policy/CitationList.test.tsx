import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { CitationList } from '@/components/policy/CitationList';
import { mockCitation1, mockCitation2 } from '../fixtures/policyFixtures';

describe('CitationList', () => {
  it('renders nothing if sources is empty or null', () => {
    const { container: c1 } = render(<CitationList sources={[]} />);
    expect(c1.firstChild).toBeNull();

    // @ts-expect-error testing null safety
    const { container: c2 } = render(<CitationList sources={null} />);
    expect(c2.firstChild).toBeNull();
  });

  it('renders source count badge and all citation cards', () => {
    render(<CitationList sources={[mockCitation1, mockCitation2]} />);

    expect(screen.getByText('Verifiable Sources')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();
    expect(screen.getByText('Expense Reimbursement Guidelines')).toBeInTheDocument();
  });

  it('toggles list visibility when header button clicked', async () => {
    const user = userEvent.setup();
    render(<CitationList sources={[mockCitation1, mockCitation2]} />);

    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();

    const toggleBtn = screen.getByRole('button', { name: /verifiable sources/i });
    await user.click(toggleBtn);

    expect(screen.queryByText('Travel Policy 2024')).not.toBeInTheDocument();
    expect(screen.getByText('(Click to expand)')).toBeInTheDocument();

    await user.click(toggleBtn);
    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();
  });
});
