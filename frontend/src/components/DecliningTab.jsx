import { useEffect, useState } from 'react';
import { api } from '../api';
import { ChartCard, ErrorBanner, Skeleton, DownloadButton, fmt, fmtPct } from './ui';

export default function DecliningTab({ filters }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    api.decliningCustomers(filters)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [filters]);

  const customers = data?.flagged_accounts || [];
  const summary = data?.summary || {};

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <DownloadButton href={api.exportUrl('declining', filters)} label="Export at-risk accounts" />
      </div>
      {error && <ErrorBanner message={error} onRetry={load} />}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Flagged</p><p className="text-2xl font-extrabold" style={{ color: '#ef4444' }}>{summary.flagged_declining ?? '—'}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Eligible</p><p className="text-2xl font-extrabold">{summary.eligible_customers ?? '—'}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Avg drop</p><p className="text-2xl font-extrabold">{fmtPct(summary.avg_drop_pct)}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Revenue at risk</p><p className="text-2xl font-extrabold">{fmt(summary.revenue_at_risk, '£')}</p></div>
      </div>

      <ChartCard title={`Ranked re-engagement list (${customers.length})`}>
        {loading ? <Skeleton h={300} /> : customers.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-muted)' }}>No declining accounts under the current filters and heuristic windows.</p>
        ) : (
          <div className="overflow-auto" style={{ maxHeight: 420 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Prior spend</th>
                  <th>Recent spend</th>
                  <th>Drop</th>
                  <th>Days since purchase</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((row) => (
                  <tr key={row.CustomerID}>
                    <td style={{ fontFamily: 'monospace' }}>{row.CustomerID}</td>
                    <td>{fmt(row.PriorSpend, '£')}</td>
                    <td>{fmt(row.RecentSpend, '£')}</td>
                    <td style={{ color: '#ef4444' }}>{fmtPct(row.VelocityDropPct)}</td>
                    <td>{row.DaysSinceLastPurchase}d</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{row.Reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ChartCard>
    </div>
  );
}
