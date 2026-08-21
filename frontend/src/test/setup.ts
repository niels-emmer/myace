import '@testing-library/jest-dom';
import { vi } from 'vitest';

// jsdom doesn't implement matchMedia, but ThemeProvider (and anything else
// reading prefers-color-scheme) calls it on mount. Default to light.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
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
