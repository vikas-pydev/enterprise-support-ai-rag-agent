import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Automatically cleanup DOM after each test
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// Mock window.matchMedia for theme toggle & responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock scrollIntoView for chat auto-scrolling
Element.prototype.scrollIntoView = vi.fn();

// Ensure navigator.clipboard is mockable and configurable for user-event
if (!navigator.clipboard) {
  Object.defineProperty(navigator, 'clipboard', {
    writable: true,
    configurable: true,
    value: {
      writeText: vi.fn().mockResolvedValue(undefined),
      readText: vi.fn().mockResolvedValue(''),
    },
  });
} else {
  try {
    Object.defineProperty(navigator.clipboard, 'writeText', {
      writable: true,
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
  } catch {
    // Ignore if already configured
  }
}
