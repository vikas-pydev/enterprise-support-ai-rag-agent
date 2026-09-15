import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ApprovalCard } from '@/components/agent/ApprovalCard';

describe('ApprovalCard', () => {
  it('renders pending approval card with reason, target worker, and action buttons', () => {
    const handleDecision = vi.fn();
    render(
      <ApprovalCard
        approvalId="appr_req_123"
        reason="Sensitive salary lookup requires authorization."
        targetWorker="Employee Records"
        approvalStatus="pending"
        onDecision={handleDecision}
      />
    );

    expect(screen.getByText('Human Approval Required')).toBeInTheDocument();
    expect(screen.getByText('HITL Gated')).toBeInTheDocument();
    expect(screen.getByText('appr_req_123')).toBeInTheDocument();
    expect(screen.getByText('Sensitive salary lookup requires authorization.')).toBeInTheDocument();
    expect(screen.getByText('Employee Records')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: /approve & continue/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });

  it('triggers approve decision with optional notes', async () => {
    const user = userEvent.setup();
    const handleDecision = vi.fn().mockResolvedValue(undefined);

    render(
      <ApprovalCard
        approvalId="appr_req_123"
        approvalStatus="pending"
        onDecision={handleDecision}
      />
    );

    const notesInput = screen.getByPlaceholderText(/e.g. Authorized by HR Operations Director/i);
    await user.type(notesInput, 'Approved by Legal');

    const approveBtn = screen.getByRole('button', { name: /approve & continue/i });
    await user.click(approveBtn);

    expect(handleDecision).toHaveBeenCalledWith('appr_req_123', 'approve', 'Approved by Legal');
  });

  it('triggers reject decision', async () => {
    const user = userEvent.setup();
    const handleDecision = vi.fn().mockResolvedValue(undefined);

    render(
      <ApprovalCard
        approvalId="appr_req_123"
        approvalStatus="pending"
        onDecision={handleDecision}
      />
    );

    const rejectBtn = screen.getByRole('button', { name: /^reject$/i });
    await user.click(rejectBtn);

    expect(handleDecision).toHaveBeenCalledWith('appr_req_123', 'reject', undefined);
  });

  it('displays authorized resolved state when approvalStatus is approved', () => {
    const handleDecision = vi.fn();
    render(
      <ApprovalCard
        approvalId="appr_req_123"
        approvalStatus="approved"
        approvalNotes="Authorized by CEO"
        onDecision={handleDecision}
      />
    );

    expect(screen.getByText('Operation Authorized by Operator')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toBeInTheDocument();
    expect(screen.getAllByText(/Authorized/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Authorized by CEO/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
  });

  it('displays rejected resolved state when approvalStatus is rejected', () => {
    const handleDecision = vi.fn();
    render(
      <ApprovalCard
        approvalId="appr_req_123"
        approvalStatus="rejected"
        onDecision={handleDecision}
      />
    );

    expect(screen.getByText('Operation Rejected by Operator')).toBeInTheDocument();
    expect(screen.getAllByText('Rejected').length).toBeGreaterThan(0);
  });

  it('handles decision error and displays local error banner', async () => {
    const user = userEvent.setup();
    const handleDecision = vi.fn().mockRejectedValue(new Error('Approval token expired'));

    render(
      <ApprovalCard
        approvalId="appr_req_123"
        approvalStatus="pending"
        onDecision={handleDecision}
      />
    );

    const approveBtn = screen.getByRole('button', { name: /approve & continue/i });
    await user.click(approveBtn);

    await waitFor(() => {
      expect(screen.getByText('Approval token expired')).toBeInTheDocument();
    });
  });
});
