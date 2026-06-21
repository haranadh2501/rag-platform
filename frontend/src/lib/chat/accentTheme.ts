/**
 * Selectable accent theme for the Chat Portal (M9).
 * Pure data — no React. Colors are Tailwind's own 600/700 shades, chosen
 * because they already pass WCAG AA contrast against white text.
 */

export interface AccentDefinition {
  key: string;
  label: string;
  /** Solid representative color, used by the picker swatch itself. */
  swatch: string;
  vars: {
    '--accent-50': string;
    '--accent-100': string;
    '--accent-200': string;
    '--accent-600': string;
    '--accent-700': string;
  };
}

export const ACCENTS: AccentDefinition[] = [
  {
    key: 'indigo',
    label: 'Indigo',
    swatch: '#4f46e5',
    vars: {
      '--accent-50': '#eef2ff',
      '--accent-100': '#e0e7ff',
      '--accent-200': '#c7d2fe',
      '--accent-600': '#4f46e5',
      '--accent-700': '#4338ca',
    },
  },
  {
    key: 'blue',
    label: 'Blue',
    swatch: '#2563eb',
    vars: {
      '--accent-50': '#eff6ff',
      '--accent-100': '#dbeafe',
      '--accent-200': '#bfdbfe',
      '--accent-600': '#2563eb',
      '--accent-700': '#1d4ed8',
    },
  },
  {
    key: 'emerald',
    label: 'Emerald',
    swatch: '#059669',
    vars: {
      '--accent-50': '#ecfdf5',
      '--accent-100': '#d1fae5',
      '--accent-200': '#a7f3d0',
      '--accent-600': '#059669',
      '--accent-700': '#047857',
    },
  },
  {
    key: 'rose',
    label: 'Rose',
    swatch: '#e11d48',
    vars: {
      '--accent-50': '#fff1f2',
      '--accent-100': '#ffe4e6',
      '--accent-200': '#fecdd3',
      '--accent-600': '#e11d48',
      '--accent-700': '#be123c',
    },
  },
  {
    key: 'violet',
    label: 'Violet',
    swatch: '#7c3aed',
    vars: {
      '--accent-50': '#f5f3ff',
      '--accent-100': '#ede9fe',
      '--accent-200': '#ddd6fe',
      '--accent-600': '#7c3aed',
      '--accent-700': '#6d28d9',
    },
  },
];

export const DEFAULT_ACCENT_KEY = ACCENTS[0].key;
export const ACCENT_STORAGE_KEY = 'chat-accent-color';

export function getAccentByKey(key: string | null | undefined): AccentDefinition {
  return ACCENTS.find((a) => a.key === key) ?? ACCENTS[0];
}
