import { useEffect, useState } from 'react';
import { DollarSign, Users, ShoppingCart, Package, TrendingUp, UserMinus } from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';
import { api } from '../api';
import { KpiCard, ChartCard, ErrorBanner, Skeleton, DownloadButton, CustomTooltip, fmt, fmtPct } from './ui';

function plainInsight(text) {
  return String(text).replace(/\*\*/g, '');
}

export default function OverviewTab({ filters }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    api.overview(filters)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [filters]);

  const kpis = data?.kpis || {};
  const monthly = data?.monthly_trend || [];
  const drivers = data?.drivers || {};

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <DownloadButton href={api.exportUrl('monthly', filters)} label="Export monthly sales" />
      </div>

      {error && <ErrorBanner message={error} onRetry={load} />}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard loading={loading} icon={DollarSign} title="Positive sales" color="#10b981"
          value={fmt(kpis.total_positive_sales, '£')}
          sub={`AOV ${fmt(kpis.avg_order_value, '£')}`} />
        <KpiCard loading={loading} icon={ShoppingCart} title="Distinct invoices" color="#38bdf8"
          value={fmt(kpis.distinct_invoices)}
          sub={`${fmt(kpis.total_quantity)} units`} />
        <KpiCard loading={loading} icon={Users} title="Identified customers" color="#818cf8"
          value={fmt(kpis.unique_customers)} />
        <KpiCard loading={loading} icon={Package} title="Distinct products" color="#f59e0b"
          value={fmt(kpis.distinct_products)} />
        <KpiCard loading={loading} icon={TrendingUp} title="Pareto (top 20%)" color="#e879f9"
          value={fmtPct(data?.pareto_share)}
          sub="of identified customer revenue" />
        <KpiCard loading={loading} icon={UserMinus} title="Guest invoices" color="#fb923c"
          value={fmt(kpis.guest_orders)} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <ChartCard title="Monthly positive sales" style={{ gridColumn: 'span 2' }}>
          {loading ? <Skeleton h={220} /> : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="YearMonth" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickFormatter={(v) => fmt(v, '£')} />
                <Tooltip content={<CustomTooltip formatter={(v) => fmt(v, '£')} />} />
                <Line type="monotone" dataKey="PositiveSales" name="Sales" stroke="#38bdf8" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Revenue drivers">
          {loading ? <Skeleton h={220} /> : (
            <div className="space-y-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
              <p>Top 10 products: <strong className="text-white">{fmtPct(drivers.top_10_product_share)}</strong></p>
              <p>Top market: <strong className="text-white">{drivers.top_country}</strong> ({fmtPct(drivers.top_country_share)})</p>
              <p>Latest month: <strong className="text-white">{drivers.latest_month}</strong></p>
              <p>MoM change: <strong className="text-white">{fmtPct(drivers.mom_pct_change)}</strong></p>
            </div>
          )}
        </ChartCard>
      </div>

      {!loading && data?.insights?.length > 0 && (
        <div className="glass-card p-5 space-y-3">
          <h3 className="font-semibold text-sm text-white">Computed insights</h3>
          {data.insights.map((insight) => (
            <p key={insight} className="text-sm" style={{ color: 'var(--text-secondary)' }}>{plainInsight(insight)}</p>
          ))}
        </div>
      )}
    </div>
  );
}
