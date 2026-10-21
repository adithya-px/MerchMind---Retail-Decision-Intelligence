// Shared reusable UI primitives

export function KpiCard({ title, value, sub, icon: Icon, color = 'var(--accent-cyan)', loading }) {
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
    <div className="flex items-center gap-3 p-4 rounded-xl my-4"
      style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)' }}>
      <div className="flex-1">
        <p className="text-sm font-medium" style={{ color: '#fca5a5' }}>⚠ {message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="text-xs px-3 py-1.5 rounded-lg font-semibold"
          style={{ background: 'rgba(239,68,68,0.2)', color: '#fca5a5', border: 'none', cursor: 'pointer' }}>
          Retry
        </button>
      )}
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
    <a
      href={href}
      download
      className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors"
      style={{
        background: 'rgba(56,189,248,0.1)',
        color: 'var(--accent-cyan)',
        border: '1px solid var(--border-accent)',
        textDecoration: 'none',
      }}
    >
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
        <p key={i} style={{ color: entry.color || 'var(--accent-cyan)' }}>
          {entry.name}: <strong>{formatter ? formatter(entry.value) : entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

export function SegmentBadge({ segment }) {
  const COLORS = {
    'Champions': { bg: 'rgba(16,185,129,0.15)', color: '#10b981' },
    'Champions (Top Tier)': { bg: 'rgba(16,185,129,0.15)', color: '#10b981' },
    'Loyal Customers': { bg: 'rgba(56,189,248,0.15)', color: '#38bdf8' },
    'High-Value Core': { bg: 'rgba(56,189,248,0.15)', color: '#38bdf8' },
    'Promising High-Spenders': { bg: 'rgba(129,140,248,0.15)', color: '#818cf8' },
    'Recent New Customers': { bg: 'rgba(251,191,36,0.15)', color: '#fbbf24' },
    'At Risk': { bg: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
    'At Risk / Slipping': { bg: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
    'Hibernating': { bg: 'rgba(100,116,139,0.15)', color: '#94a3b8' },
    'Hibernating / Inactive': { bg: 'rgba(100,116,139,0.15)', color: '#94a3b8' },
  };
  const style = COLORS[segment] || { bg: 'rgba(148,163,184,0.12)', color: 'var(--text-secondary)' };
  return (
    <span className="segment-badge" style={{ background: style.bg, color: style.color }}>
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
