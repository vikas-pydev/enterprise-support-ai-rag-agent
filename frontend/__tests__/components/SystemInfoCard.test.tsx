import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { SystemInfoCard } from '@/components/SystemInfoCard';

describe('SystemInfoCard', () => {
  it('renders collapsed accordion header by default', () => {
    render(<SystemInfoCard />);

    expect(screen.getByText('System Architecture & Technical Overview')).toBeInTheDocument();
  });

  it('expands on click and displays tech stack chips and REST API endpoints', async () => {
    const user = userEvent.setup();
    render(<SystemInfoCard />);

    const toggleBtn = screen.getByRole('button', { name: /system architecture & technical overview/i });
    await user.click(toggleBtn);

    expect(screen.getByText('Next.js 16 (App Router)')).toBeInTheDocument();
    expect(screen.getByText('TypeScript 5')).toBeInTheDocument();
    expect(screen.getAllByText('LangGraph Multi-Agent').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Hybrid RAG/i).length).toBeGreaterThan(0);
    expect(screen.getByText('PostgreSQL & psycopg3')).toBeInTheDocument();
    expect(screen.getAllByText('/api/v1/ask').length).toBeGreaterThan(0);
    expect(screen.getAllByText('/api/v1/agent/chat').length).toBeGreaterThan(0);
  });
});
