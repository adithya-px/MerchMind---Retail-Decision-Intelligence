// Shared reusable UI primitives

export function KpiCard({ title, value, sub, icon: Icon, color = 'var(--link)', loading }) {
  if (loading) {
    return (
      <div className="kpi-card">
        <div className="shimmer h-4 w-24 rounded mb-3" />
        <div className="shimmer h-8 w-32 rounded mb-2" />
        <div className="shimmer h-3 w-20 rounded" />
      </div>
    );
  }
  return (
    <div className="kpi-card">
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{title}</p>
        {Icon && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}18` }}>
            <Icon size={16} style={{ color }} />
          </div>
        )}
      </div>
      <p className="text-2xl font-extrabold text-white leading-tight">{value ?? '—'}</p>
      {sub && <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{sub}</p>}
    </div>
  );
}

export function SectionTitle({ children, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="font-bold text-base text-white">{children}</h2>
      {action}
    </div>
  );
}

export function ChartCard({ title, children, style, action }) {
  return (
    <div className="glass-card p-5" style={style}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm text-white">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }) {
  return (
    <div className="error-banner">
      <div className="flex-1">
        <p className="error-banner__text">⚠ {message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="error-banner__retry">
          Retry
        </button>
      )}
    </div>
  );
}

export function Loader({ label }) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="loader" aria-hidden="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <span key={i} className="loader-square" />
        ))}
      </div>
      {label && <p style={{ color: 'var(--text-secondary)' }}>{label}</p>}
    </div>
  );
}

export function Skeleton({ h = 20, w = '100%', className = '' }) {
  return <div className={`shimmer rounded ${className}`} style={{ height: h, width: w }} />;
}

export function FilterSelect({ label, value, onChange, options, disabled }) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{label}</label>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-dim)',
          color: 'var(--text-primary)',
          borderRadius: 8,
          padding: '6px 28px 6px 10px',
          fontSize: '0.85rem',
          cursor: 'pointer',
          outline: 'none',
          appearance: 'none',
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2364748b' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 8px center',
        }}
      >
        {options.map((o) => (
          <option key={typeof o === 'string' ? o : o.value} value={typeof o === 'string' ? o : o.value}>
            {typeof o === 'string' ? o : o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function DownloadButton({ href, label }) {
  return (
    <a href={href} download className="download-btn">
      ↓ {label}
    </a>
  );
}

export function CustomTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <p className="font-semibold mb-1 text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color || 'var(--text-primary)' }}>
          {entry.name}: <strong>{formatter ? formatter(entry.value) : entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

const SEGMENT_TOKENS = {
  'Champions': 'champions',
  'Champions (Top Tier)': 'champions',
  'Loyal Customers': 'loyal',
  'High-Value Core': 'loyal',
  'Promising High-Spenders': 'promising',
  'Recent New Customers': 'recent',
  'At Risk': 'risk',
  'At Risk / Slipping': 'risk',
  'Hibernating': 'hibernate',
  'Hibernating / Inactive': 'hibernate',
};

export function SegmentBadge({ segment }) {
  const key = SEGMENT_TOKENS[segment] || 'neutral';
  return (
    <span
      className="segment-badge"
      style={{ background: `var(--seg-${key}-bg)`, color: `var(--seg-${key}-fg)` }}
    >
      {segment}
    </span>
  );
}

export function fmt(n, prefix = '') {
  if (n === null || n === undefined) return '—';
  if (Math.abs(n) >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e3) return `${prefix}${(n / 1e3).toFixed(1)}K`;
  return `${prefix}${Number(n).toLocaleString()}`;
}

export function fmtPct(n) {
  if (n === null || n === undefined) return '—';
  return `${(+n).toFixed(1)}%`;
}
