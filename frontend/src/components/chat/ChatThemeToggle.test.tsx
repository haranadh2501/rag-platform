import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatThemeProvider from './ChatThemeProvider';
import ChatThemeToggle from './ChatThemeToggle';

const STORAGE_KEY = 'chat-theme';

function mockMatchMedia(prefersDark: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: prefersDark,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
}

function renderToggle() {
  return render(
    <ChatThemeProvider>
      <ChatThemeToggle />
    </ChatThemeProvider>,
  );
}

describe('ChatThemeToggle', () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockMatchMedia(false);
  });

  it('defaults to light when no stored value and no system dark preference', () => {
    renderToggle();
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false');
  });

  it('defaults to dark when system prefers dark and no stored value exists', () => {
    mockMatchMedia(true);
    renderToggle();
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });

  it('restores a previously stored theme on mount', () => {
    window.localStorage.setItem(STORAGE_KEY, 'dark');
    renderToggle();
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });

  it('toggling persists the new theme to localStorage and applies the dark class scoped to chat', () => {
    const { container } = renderToggle();
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).not.toContain('dark');

    fireEvent.click(screen.getByRole('button'));

    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('dark');
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
    expect(wrapper.className).toContain('dark');
  });
});
