import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { Header } from '@/components/Header';

describe('Header', () => {
  it('renders application branding, production version badge, and links', () => {
    render(<Header />);

    expect(screen.getByText('Enterprise Support AI Agent')).toBeInTheDocument();
    expect(screen.getByText('Production v1.0')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open fastapi swagger documentation/i })).toHaveAttribute(
      'href',
      'http://127.0.0.1:8000/docs'
    );
  });

  it('opens Architecture modal when Architecture button is clicked', async () => {
    const user = userEvent.setup();
    render(<Header />);

    const archBtn = screen.getByRole('button', { name: /view system architecture and tech stack/i });
    await user.click(archBtn);

    expect(screen.getByText('System Architecture & Technical Reference')).toBeInTheDocument();
  });
});
