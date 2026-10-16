import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SourceInspectorPanel } from '@/components/policy/SourceInspectorPanel';
import { mockCitation1 } from '../fixtures/policyFixtures';
import { INDEXED_POLICY_DOCUMENTS } from '@/lib/knowledge/documents';

describe('SourceInspectorPanel', () => {
  it('renders citation details when citation is selected', () => {
    const handleClose = vi.fn();
    render(
      <SourceInspectorPanel
        isOpen={true}
        onClose={handleClose}
        selectedCitation={mockCitation1}
      />
    );

    expect(screen.getByText('Citation Inspector')).toBeInTheDocument();
    expect(screen.getByText('Travel Policy 2024')).toBeInTheDocument();
    expect(screen.getByText(/Rank #1/i)).toBeInTheDocument();
    expect(screen.getByText(/The standard domestic meal per diem allowance is \$75 per day/i)).toBeInTheDocument();
  });

  it('renders full document preview when policy document is selected', () => {
    const handleClose = vi.fn();
    const doc = INDEXED_POLICY_DOCUMENTS[0]; // Travel policy

    render(
      <SourceInspectorPanel
        isOpen={true}
        onClose={handleClose}
        selectedDocument={doc}
      />
    );

    expect(screen.getByText('Document Preview')).toBeInTheDocument();
    expect(screen.getByText('Corporate Travel and Expense Policy')).toBeInTheDocument();
    expect(screen.getByText(/All business travel must receive written manager pre-approval/i)).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();

    render(
      <SourceInspectorPanel
        isOpen={true}
        onClose={handleClose}
        selectedCitation={mockCitation1}
      />
    );

    const closeBtn = screen.getByRole('button', { name: /close source inspector/i });
    await user.click(closeBtn);

    expect(handleClose).toHaveBeenCalled();
  });
});
