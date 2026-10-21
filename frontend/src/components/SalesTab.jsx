import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer, BarChart, Bar, AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';
import { api } from '../api';
import { ChartCard, ErrorBanner, Skeleton, DownloadButton, CustomTooltip, fmt, fmtPct } from './ui';

export default function SalesTab({ filters }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    api.sales(filters)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [filters]);

  const daily = (data?.daily_trend || []).slice(-90);
  const hourly = data?.hourly_trend || [];
  const dowData = data?.dow_trend || [];
  const topProducts = data?.top_products_revenue || [];
  const topCustomers = data?.top_customers || [];
  const countries = data?.country_breakdown || [];
  const heatmap = data?.demand_timing || [];
  const hours = useMemo(() => [...new Set(heatmap.map((row) => row.Hour))].sort((a, b) => a - b), [heatmap]);
  const days = useMemo(() => {
    const order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const present = [...new Set(heatmap.map((row) => row.DayOfWeek))];
    return order.filter((day) => present.includes(day));
  }, [heatmap]);
  const heatMax = Math.max(1, ...heatmap.map((row) => row.PositiveSales || 0));

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <DownloadButton href={api.exportUrl('sales', filters)} label="Export filtered sales" />
      </div>

      {error && <ErrorBanner message={error} onRetry={load} />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="kpi-card">
          <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Top 20% customers</p>
          <p className="text-2xl font-extrabold text-white">{fmtPct(data?.pareto?.top_20_share_pct)}</p>
        </div>
        <div className="kpi-card">
          <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Top 10 product share</p>
          <p className="text-2xl font-extrabold text-white">{fmtPct(data?.drivers?.top_10_product_share)}</p>
        </div>
        <div className="kpi-card">
          <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Dominant market</p>
          <p className="text-2xl font-extrabold text-white">{data?.drivers?.top_country || '—'}</p>
        </div>
      </div>

      <ChartCard title="Daily positive sales (last 90 days in range)">
        {loading ? <Skeleton h={220} /> : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="Date" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} interval={6} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
              <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
              <Area type="monotone" dataKey="PositiveSales" stroke="#38bdf8" strokeWidth={2} fill="#38bdf833" name="Sales" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <ChartCard title="Revenue by hour of day">
          {loading ? <Skeleton h={200} /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={hourly}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="hour" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(h) => `${h}:00`} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
                <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
                <Bar dataKey="revenue" fill="#818cf8" radius={[3, 3, 0, 0]} name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
        <ChartCard title="Revenue by weekday">
          {loading ? <Skeleton h={200} /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={dowData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
                <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
                <Bar dataKey="revenue" fill="#10b981" radius={[3, 3, 0, 0]} name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <ChartCard title="Top products by revenue">
          {loading ? <Skeleton h={250} /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={topProducts} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
                <YAxis type="category" dataKey="Description" width={140} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
                <Bar dataKey="Value" fill="#38bdf8" radius={[0, 3, 3, 0]} name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
        <ChartCard title="Top identified customers">
          {loading ? <Skeleton h={250} /> : (
            <div className="overflow-auto" style={{ maxHeight: 250 }}>
              <table className="data-table">
                <thead>
                  <tr><th>#</th><th>Customer</th><th>Revenue</th><th>Orders</th></tr>
                </thead>
                <tbody>
                  {topCustomers.map((row, i) => (
                    <tr key={row.customer_id}>
                      <td style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                      <td style={{ fontFamily: 'monospace' }}>{row.customer_id}</td>
                      <td style={{ color: 'var(--accent-green)' }}>{fmt(row.revenue, '£')}</td>
                      <td>{row.orders}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <ChartCard title="Country revenue">
          {loading ? <Skeleton h={220} /> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={countries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="Country" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
                <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
                <Bar dataKey="PositiveSales" fill="#f59e0b" radius={[3, 3, 0, 0]} name="Sales" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
        <ChartCard title="Pareto concentration">
          {loading ? <Skeleton h={220} /> : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data?.pareto?.curve || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="customer_pct" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} unit="%" />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} unit="%" />
                <Tooltip content={<CustomTooltip formatter={(v) => `${v}%`} />} />
                <Line type="monotone" dataKey="revenue_pct" name="Revenue share" stroke="#818cf8" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      <ChartCard title="Weekday × hour sales intensity">
        {loading ? <Skeleton h={180} /> : heatmap.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No timing data in the selected range.</p>
        ) : (
          <div className="overflow-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Day</th>
                  {hours.map((hour) => <th key={hour}>{hour}</th>)}
                </tr>
              </thead>
              <tbody>
                {days.map((day) => (
                  <tr key={day}>
                    <td>{day.slice(0, 3)}</td>
                    {hours.map((hour) => {
                      const cell = heatmap.find((row) => row.DayOfWeek === day && row.Hour === hour);
                      const value = cell?.PositiveSales || 0;
                      const intensity = value / heatMax;
                      return (
                        <td key={`${day}-${hour}`} style={{ background: `rgba(56,189,248,${intensity * 0.55})`, textAlign: 'center' }}>
                          {value ? fmt(value) : ''}
                        </td>
                      );
                    })}
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
