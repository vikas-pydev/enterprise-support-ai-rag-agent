import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ArchitectureModal } from '@/components/ArchitectureModal';

describe('ArchitectureModal', () => {
  it('returns null when isOpen is false', () => {
    const { container } = render(<ArchitectureModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders modal dialog and switches across tabs', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    render(<ArchitectureModal isOpen={true} onClose={handleClose} />);

    expect(screen.getByText('System Architecture & Technical Reference')).toBeInTheDocument();
    expect(screen.getByText('System Vision & Core Pillars')).toBeInTheDocument();

    // Switch to RAG tab
    await user.click(screen.getByRole('button', { name: /hybrid rag pipeline/i }));
    expect(screen.getByText('Two-Stage Retrieval & Refusal Architecture')).toBeInTheDocument();

    // Switch to LangGraph tab
    await user.click(screen.getByRole('button', { name: /langgraph multi-agent/i }));
    expect(screen.getByText('Supervisor-Worker Orchestration Graph')).toBeInTheDocument();

    // Switch to PostgreSQL tab
    await user.click(screen.getByRole('button', { name: /postgresql schema/i }));
    expect(screen.getByText('Normalized Relational Schema')).toBeInTheDocument();

    // Switch to REST API tab
    await user.click(screen.getByRole('button', { name: /rest api matrix/i }));
    expect(screen.getByText(/FastAPI Endpoints/i)).toBeInTheDocument();

    // Close button
    await user.click(screen.getByRole('button', { name: /close architecture modal/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
