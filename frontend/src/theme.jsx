import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'merchmind-theme';

/*
 * Chart palettes. Dark mode keeps the original product palette unchanged;
 * light mode follows Lightdesign.md (lime is the only accent, ink/slate for
 * secondary series).
 */
const PALETTES = {
  dark: {
    series: ['#5ee7ff', '#7aa8ff', '#22d3ee', '#8ed6ff', '#4ea8ff', '#a7d8ff', '#74c0fc'],
    kpi: ['#22d3ee', '#5ee7ff', '#7aa8ff', '#8ed6ff', '#4ea8ff', '#a7d8ff'],
    line: '#5ee7ff',
    areaStroke: '#5ee7ff',
    areaFill: 'rgba(94,231,255,0.22)',
    bar: '#7aa8ff',
    barAlt: '#5ee7ff',
    grid: 'rgba(148,197,255,0.1)',
    baseline: '#a4c5f5',
    upper: 'rgba(94,231,255,0.3)',
    surge: '#7dd3fc',
    drop: '#4ea8ff',
    heatRgb: '94,231,255',
    positive: '#22d3ee',
  },
  light: {
    series: ['#A9CC1E', '#0B1014', '#3E9B2F', '#9AA5B1', '#D9473F', '#7C8A12', '#6B7785'],
    kpi: ['#3E9B2F', '#A9CC1E', '#0B1014', '#6B7785', '#8FAF1A', '#9AA5B1'],
    line: '#0B1014',
    areaStroke: '#0B1014',
    areaFill: 'rgba(216,255,62,0.35)',
    bar: '#A9CC1E',
    barAlt: '#0B1014',
    grid: 'rgba(11,16,20,0.08)',
    baseline: '#9AA5B1',
    upper: 'rgba(169,204,30,0.55)',
    surge: '#A9CC1E',
    drop: '#D9473F',
    heatRgb: '169,204,30',
    positive: '#3E9B2F',
  },
};

const ThemeContext = createContext(null);

function readInitialTheme() {
  if (typeof document === 'undefined') return 'dark';
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'light' || attr === 'dark') return attr;
  return 'dark';
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    // Keep native form controls (date pickers, selects) in the right scheme.
    document.documentElement.style.colorScheme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Storage can be unavailable (private mode); theme still applies for the session.
    }
  }, [theme]);

  const setTheme = useCallback((next) => {
    setThemeState(next === 'light' ? 'light' : 'dark');
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme, chart: PALETTES[theme] || PALETTES.dark }),
    [theme, setTheme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}
