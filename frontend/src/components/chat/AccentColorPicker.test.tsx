import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AccentThemeProvider from './AccentThemeProvider';
import AccentColorPicker from './AccentColorPicker';
import { ACCENT_STORAGE_KEY } from '../../lib/chat/accentTheme';

function renderPicker() {
  return render(
    <AccentThemeProvider>
      <AccentColorPicker />
    </AccentThemeProvider>,
  );
}

describe('AccentColorPicker', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('defaults to indigo and marks it selected', () => {
    renderPicker();
    expect(screen.getByRole('button', { name: 'Indigo accent color' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('persists the selected accent to localStorage and updates selection state', () => {
    renderPicker();
    fireEvent.click(screen.getByRole('button', { name: 'Emerald accent color' }));

    expect(window.localStorage.getItem(ACCENT_STORAGE_KEY)).toBe('emerald');
    expect(screen.getByRole('button', { name: 'Emerald accent color' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Indigo accent color' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('restores a previously stored accent on mount', () => {
    window.localStorage.setItem(ACCENT_STORAGE_KEY, 'rose');
    renderPicker();
    expect(screen.getByRole('button', { name: 'Rose accent color' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('applies the accent as CSS variables for descendants to consume', () => {
    const { container } = renderPicker();
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.style.getPropertyValue('--accent-600')).toBe('#4f46e5');

    fireEvent.click(screen.getByRole('button', { name: 'Blue accent color' }));
    expect(wrapper.style.getPropertyValue('--accent-600')).toBe('#2563eb');
  });
});
