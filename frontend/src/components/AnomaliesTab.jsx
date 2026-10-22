import { useEffect, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { api } from '../api';
import { useTheme } from '../theme';
import { ChartCard, ErrorBanner, Skeleton, DownloadButton, CustomTooltip, fmt } from './ui';

export default function AnomaliesTab({ filters }) {
  const { chart } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    api.anomalies(filters)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [filters]);

  const anomalies = data?.anomalies || [];
  const daily = data?.daily_series || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <DownloadButton href={api.exportUrl('anomalies', filters)} label="Export anomalies" />
      </div>
      {error && <ErrorBanner message={error} onRetry={load} />}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Anomalies</p><p className="text-2xl font-extrabold">{data?.total_anomalies ?? '—'}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Surges</p><p className="text-2xl font-extrabold">{data?.summary?.surge_count ?? '—'}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Drops</p><p className="text-2xl font-extrabold">{data?.summary?.drop_count ?? '—'}</p></div>
        <div className="kpi-card"><p className="text-xs" style={{ color: 'var(--text-muted)' }}>Days scored</p><p className="text-2xl font-extrabold">{data?.summary?.total_days ?? '—'}</p></div>
      </div>

      <ChartCard title="Daily sales vs rolling baseline">
        {loading ? <Skeleton h={280} /> : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
              <XAxis dataKey="Date" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} interval={Math.max(0, Math.floor(daily.length / 12))} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
              <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
              <Area type="monotone" dataKey="UpperBound" stroke={chart.upper} fill="transparent" name="Upper bound" />
              <Area type="monotone" dataKey="Baseline" stroke={chart.baseline} fill="transparent" name="Baseline" />
              <Area type="monotone" dataKey="Sales" stroke={chart.areaStroke} fill={chart.areaFill} name="Sales" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <ChartCard title="Anomaly events">
        {loading ? <Skeleton h={180} /> : anomalies.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-muted)' }}>No anomalies in this cohort.</p>
        ) : (
          <div className="space-y-3" style={{ maxHeight: 420, overflowY: 'auto' }}>
            {anomalies.map((event) => {
              const isSurge = String(event.AnomalyType).toLowerCase().includes('surge');
              const color = isSurge ? chart.surge : chart.drop;
              return (
                <div key={event.Date} className="p-4 rounded-xl" style={{ border: `1px solid ${color}40`, background: `${color}14` }}>
                  <p className="font-semibold text-white">{event.Date} · {event.AnomalyType}</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Sales {fmt(event.Sales, '£')} vs baseline {fmt(event.Baseline, '£')}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </ChartCard>
    </div>
  );
}
