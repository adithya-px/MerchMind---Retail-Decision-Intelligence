import { useEffect, useState } from 'react';
import { api } from '../api';
import { ChartCard, ErrorBanner, Skeleton, fmt, fmtPct } from './ui';

export default function AuditTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    api.auditLog()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  const guest = data?.guest_metrics || {};
  const trail = data?.audit_trail || [];

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} onRetry={load} />}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Guest revenue share</p><p className="text-2xl font-extrabold">{fmtPct(guest.guest_revenue_share_pct)}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Guest rows</p><p className="text-2xl font-extrabold">{fmt(guest.guest_rows)}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Identified customers</p><p className="text-2xl font-extrabold">{fmt(guest.identified_customers_count)}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Cancellations</p><p className="text-2xl font-extrabold">{fmt(data?.cancellations_summary?.total_cancellations)}</p></div>
      </div>
      <ChartCard title="Cleaning audit trail">
        {loading ? <Skeleton h={240} /> : (
          <div className="overflow-auto" style={{ maxHeight: 480 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Stage</th>
                  <th>Action</th>
                  <th>Rows before</th>
                  <th>Affected</th>
                  <th>Rows after</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {trail.map((row) => (
                  <tr key={`${row.Step}-${row.Stage}`}>
                    <td>{row.Step}</td>
                    <td>{row.Stage}</td>
                    <td>{row.Action}</td>
                    <td>{fmt(row['Rows Before'])}</td>
                    <td>{fmt(row['Rows Affected'])}</td>
                    <td>{fmt(row['Rows After'])}</td>
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
