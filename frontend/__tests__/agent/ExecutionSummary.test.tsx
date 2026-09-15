import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ExecutionSummary } from '@/components/agent/ExecutionSummary';
import { mockStep1, mockStep2 } from '../fixtures/agentFixtures';

describe('ExecutionSummary', () => {
  it('renders completed status badge, duration, steps, and worker chips', () => {
    render(
      <ExecutionSummary
        status="completed"
        durationMs={1250}
        totalSteps={2}
        steps={[mockStep1, mockStep2]}
        usedRag={false}
      />
    );

    expect(screen.getByText('Execution Summary:')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('1.25s')).toBeInTheDocument();
    expect(screen.getByText('2 tool steps')).toBeInTheDocument();

    // Workers involved
    expect(screen.getByText('Workers:')).toBeInTheDocument();
    expect(screen.getByText('Employee Records')).toBeInTheDocument();
    expect(screen.getByText('Travel & Expense')).toBeInTheDocument();
  });

  it('renders pending approval status badge and RAG chip when usedRag is true', () => {
    render(
      <ExecutionSummary
        status="pending_approval"
        durationMs={450}
        totalSteps={1}
        steps={[]}
        usedRag={true}
        citationCount={3}
      />
    );

    expect(screen.getByText('Pending Approval')).toBeInTheDocument();
    expect(screen.getByText('450ms')).toBeInTheDocument();
    expect(screen.getByText(/RAG Policy \(3 sources\)/i)).toBeInTheDocument();
  });

  it('renders rejected and max_steps status badges properly', () => {
    const { rerender } = render(<ExecutionSummary status="rejected" />);
    expect(screen.getByText('Action Rejected')).toBeInTheDocument();

    rerender(<ExecutionSummary status="max_steps_reached" />);
    expect(screen.getByText('Max Steps Budget')).toBeInTheDocument();

    rerender(<ExecutionSummary status="clarification_needed" />);
    expect(screen.getByText('Clarification Needed')).toBeInTheDocument();
  });
});
