import { useEffect, useState } from 'react';
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar,
} from 'recharts';
import { api } from '../api';
import { ChartCard, ErrorBanner, Skeleton, DownloadButton, SegmentBadge, fmt, fmtPct } from './ui';

const COLORS = ['#38bdf8', '#818cf8', '#10b981', '#f59e0b', '#ef4444', '#e879f9', '#fb923c'];

export default function SegmentsTab({ filters, k }) {
  const [data, setData] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeCluster, setActiveCluster] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    const params = { ...filters, k };
    Promise.all([api.customerSegments(params), api.modelDiagnostics(filters)])
      .then(([seg, diag]) => {
        setData(seg);
        setDiagnostics(diag);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [filters, k]);

  const profiles = data?.profiles || [];
  const pcaPoints = data?.pca_points || [];
  const table = data?.cohort_sample || [];
  const silhouette = diagnostics?.evaluations || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <DownloadButton href={api.exportUrl('segments', filters, { k })} label="Export segments" />
      </div>
      {error && <ErrorBanner message={error} onRetry={load} />}

      {!loading && data?.metadata && (
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Fitted k={data.metadata.n_clusters}. Silhouette {data.metadata.silhouette_score?.toFixed?.(3) ?? data.metadata.silhouette_score}.
          PCA captures {fmtPct(data.metadata.total_pca_variance_pct)} of variance. Recommended k from diagnostics: {diagnostics?.best_k ?? '—'}.
        </p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        {loading ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={120} />) : profiles.map((profile) => (
          <button
            key={profile.Cluster}
            type="button"
            className="glass-card p-4 text-left"
            onClick={() => setActiveCluster(activeCluster === profile.Cluster ? null : profile.Cluster)}
            style={{ borderColor: activeCluster === profile.Cluster ? COLORS[profile.Cluster % COLORS.length] : undefined }}
          >
            <SegmentBadge segment={profile.SegmentName} />
            <p className="text-xl font-extrabold text-white mt-2">{fmt(profile.CustomerCount)}</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>customers · {fmtPct(profile.RevenueSharePct)} revenue</p>
            <div className="mt-2 grid grid-cols-3 gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
              <div>R {profile.Recency_mean?.toFixed(0)}d</div>
              <div>F {profile.Frequency_mean?.toFixed(1)}</div>
              <div>M {fmt(profile.Monetary_mean, '£')}</div>
            </div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <ChartCard title="PCA cluster map">
          {loading ? <Skeleton h={260} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="PCA1" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} name="PCA1" />
                <YAxis dataKey="PCA2" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} name="PCA2" />
                <Tooltip content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const point = payload[0].payload;
                  return (
                    <div className="custom-tooltip">
                      <p>{point.SegmentName}</p>
                      <p>R {point.Recency} · F {point.Frequency} · M {fmt(point.Monetary, '£')}</p>
                    </div>
                  );
                }} />
                {profiles.map((profile) => (
                  <Scatter
                    key={profile.Cluster}
                    name={profile.SegmentName}
                    data={pcaPoints.filter((row) => row.SegmentName === profile.SegmentName)}
                    fill={COLORS[profile.Cluster % COLORS.length]}
                  />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
        <ChartCard title="Silhouette by k">
          {loading ? <Skeleton h={260} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={silhouette}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="k" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip />
                <Bar dataKey="SilhouetteScore" fill="#818cf8" radius={[3, 3, 0, 0]} name="Silhouette" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      <ChartCard title={`Highest-spend customers (${table.length})`}>
        {loading ? <Skeleton h={200} /> : (
          <div className="overflow-auto" style={{ maxHeight: 320 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Segment</th>
                  <th>Recency</th>
                  <th>Frequency</th>
                  <th>Monetary</th>
                </tr>
              </thead>
              <tbody>
                {table.map((row) => (
                  <tr key={row.CustomerID}>
                    <td style={{ fontFamily: 'monospace' }}>{row.CustomerID}</td>
                    <td><SegmentBadge segment={row.SegmentName} /></td>
                    <td>{row.Recency}</td>
                    <td>{row.Frequency}</td>
                    <td>{fmt(row.Monetary, '£')}</td>
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
