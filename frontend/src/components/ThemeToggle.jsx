import { useTheme } from '../theme';

/**
 * Day/night toggle (Uiverse-style switch). Unchecked = light, checked = dark.
 */
export default function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className={`theme-toggle ${className}`}>
      <input
        className="tgl-input"
        id="theme-toggle-input"
        type="checkbox"
        checked={isDark}
        onChange={toggleTheme}
        aria-label="Toggle dark mode"
      />
      <label className="tgl" htmlFor="theme-toggle-input" title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}>
        <span className="tgl-handler">
          <span className="tgl-crater tgl-crater--1" />
          <span className="tgl-crater tgl-crater--2" />
          <span className="tgl-crater tgl-crater--3" />
        </span>
        <span className="tgl-star tgl-star--1" />
        <span className="tgl-star tgl-star--2" />
        <span className="tgl-star tgl-star--3" />
        <span className="tgl-star tgl-star--4" />
        <span className="tgl-star tgl-star--5" />
        <span className="tgl-star tgl-star--6" />
      </label>
    </div>
  );
}
