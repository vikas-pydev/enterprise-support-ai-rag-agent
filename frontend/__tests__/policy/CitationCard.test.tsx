import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { CitationCard } from '@/components/policy/CitationCard';
import { mockCitation1 } from '../fixtures/policyFixtures';

describe('CitationCard', () => {
  it('renders citation metadata, rank, score, file, chunk id and snippet', () => {
    render(<CitationCard source={mockCitation1} defaultExpanded={true} />);

    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();
    expect(screen.getByText('Score: 0.942')).toBeInTheDocument();
    expect(screen.getByText('data/policies/travel_policy.md')).toBeInTheDocument();
    expect(screen.getByText('travel_meal_allowance_chunk_1')).toBeInTheDocument();
    expect(
      screen.getByText(/The standard domestic meal per diem allowance is \$75 per day/)
    ).toBeInTheDocument();
  });

  it('collapses and expands snippet when clicking card header', async () => {
    const user = userEvent.setup();
    render(<CitationCard source={mockCitation1} defaultExpanded={true} />);

    const snippetText = /The standard domestic meal per diem allowance is \$75 per day/;
    expect(screen.getByText(snippetText)).toBeInTheDocument();

    // Click header to collapse
    const titleElem = screen.getByText('Travel Policy 2024');
    await user.click(titleElem);
    expect(screen.queryByText(snippetText)).not.toBeInTheDocument();

    // Click again to re-expand
    await user.click(titleElem);
    expect(screen.getByText(snippetText)).toBeInTheDocument();
  });

  it('copies passage snippet to clipboard when copy button clicked', async () => {
    const user = userEvent.setup();
    const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    render(<CitationCard source={mockCitation1} />);

    const copyBtn = screen.getByRole('button', { name: /copy source passage/i });
    expect(copyBtn).toBeInTheDocument();

    await user.click(copyBtn);

    expect(writeTextSpy).toHaveBeenCalledWith(mockCitation1.snippet);
    await waitFor(() => {
      expect(screen.getByTitle('Copied!')).toBeInTheDocument();
    });
  });
});
