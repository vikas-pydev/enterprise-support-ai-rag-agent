import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { RetrievalDetails } from '@/components/policy/RetrievalDetails';
import { mockCitation1, mockCitation2 } from '../fixtures/policyFixtures';

describe('RetrievalDetails', () => {
  it('is collapsed by default and displays expand button', () => {
    render(<RetrievalDetails sources={[mockCitation1]} durationMs={350} />);

    expect(screen.getByText(/retrieval & grounding details/i)).toBeInTheDocument();
    expect(screen.queryByText('Hybrid Dense + BM25')).not.toBeInTheDocument();
  });

  it('expands on click and shows retrieval metrics for evidence supported response', async () => {
    const user = userEvent.setup();
    render(<RetrievalDetails sources={[mockCitation1, mockCitation2]} durationMs={420} isRefusal={false} />);

    const toggleBtn = screen.getByRole('button', { name: /retrieval & grounding details/i });
    await user.click(toggleBtn);

    expect(screen.getByText('Hybrid Dense + BM25')).toBeInTheDocument();
    expect(screen.getByText('Cross-Encoder (MiniLM)')).toBeInTheDocument();
    expect(screen.getByText('2 passages')).toBeInTheDocument();
    expect(screen.getByText('0.942')).toBeInTheDocument(); // max score
    expect(screen.getByText('420 ms')).toBeInTheDocument();
    expect(screen.getByText('Evidence Supported')).toBeInTheDocument();
  });

  it('shows Refusal verdict when isRefusal is true', async () => {
    const user = userEvent.setup();
    render(<RetrievalDetails sources={[]} isRefusal={true} />);

    const toggleBtn = screen.getByRole('button', { name: /retrieval & grounding details/i });
    await user.click(toggleBtn);

    expect(screen.getByText('Refusal (No Evidence)')).toBeInTheDocument();
    expect(screen.getByText('0 passages')).toBeInTheDocument();
  });
});
