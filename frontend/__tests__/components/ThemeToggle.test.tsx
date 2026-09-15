import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ThemeToggle } from '@/components/ThemeToggle';

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
  });

  it('renders theme toggle button with accessible aria-label', () => {
    render(<ThemeToggle />);

    const toggleBtn = screen.getByRole('button', { name: /switch to light mode/i });
    expect(toggleBtn).toBeInTheDocument();
  });

  it('toggles from dark to light mode on click', async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    const toggleBtn = screen.getByRole('button', { name: /switch to light mode/i });
    await user.click(toggleBtn);

    expect(localStorage.getItem('theme')).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);

    // Button label updates to switch back to dark mode
    expect(screen.getByRole('button', { name: /switch to dark mode/i })).toBeInTheDocument();
  });

  it('toggles from light to dark mode on subsequent click', async () => {
    const user = userEvent.setup();
    localStorage.setItem('theme', 'light');
    render(<ThemeToggle />);

    const toggleBtn = screen.getByRole('button', { name: /switch to dark mode/i });
    await user.click(toggleBtn);

    expect(localStorage.getItem('theme')).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
