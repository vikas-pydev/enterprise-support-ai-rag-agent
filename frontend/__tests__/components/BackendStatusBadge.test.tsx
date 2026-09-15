import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BackendStatusBadge } from '@/components/BackendStatusBadge';
import { apiClient } from '@/lib/api/client';
import { mockHealthResponse } from '../fixtures/policyFixtures';

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    healthCheck: vi.fn(),
    getBaseUrl: vi.fn().mockReturnValue('http://localhost:8000'),
  },
}));

describe('BackendStatusBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders online state when healthCheck succeeds', async () => {
    vi.mocked(apiClient.healthCheck).mockResolvedValueOnce(mockHealthResponse);
    render(<BackendStatusBadge />);

    await waitFor(() => {
      expect(screen.getByText(/Online/i)).toBeInTheDocument();
      expect(screen.getByText(/v1\.0\.0/i)).toBeInTheDocument();
    });
  });

  it('renders offline state when healthCheck fails', async () => {
    vi.mocked(apiClient.healthCheck).mockRejectedValueOnce(new Error('Connection refused'));
    render(<BackendStatusBadge />);

    await waitFor(() => {
      expect(screen.getByText(/Offline/i)).toBeInTheDocument();
    });
  });

  it('toggles diagnostics popover on click', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.healthCheck).mockResolvedValueOnce(mockHealthResponse);
    render(<BackendStatusBadge />);

    await waitFor(() => {
      expect(screen.getByText(/Online/i)).toBeInTheDocument();
    });

    const badgeBtn = screen.getByRole('button', { name: /backend status: online/i });
    await user.click(badgeBtn);

    expect(screen.getByText('Backend Diagnostics')).toBeInTheDocument();
    expect(screen.getByText('GET /health')).toBeInTheDocument();
  });
});
