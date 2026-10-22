import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { api } from '../api';
import { useTheme } from '../theme';
import { ChartCard, ErrorBanner, Skeleton, DownloadButton, CustomTooltip, fmt, fmtPct } from './ui';

const FEATURE_LABELS = {
  log_recency: 'Days since last purchase (log)',
  log_frequency: 'Orders in 90d (log)',
  log_monetary: 'Spend in 90d (log)',
  avg_order_value: 'Average order value',
  tenure_days: 'Customer tenure (days)',
  median_gap_days: 'Typical days between orders',
  recency_over_gap: 'Silence vs typical gap',
  spend_ratio_60: 'Spend last 60d vs prior 60d',
  orders_ratio_60: 'Orders last 60d vs prior 60d',
  distinct_products: 'Distinct products bought',
  return_rate: 'Return / cancellation rate',
  is_uk: 'UK customer',
};

const captionStyle = { color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 12, lineHeight: 1.5 };

export default function PredictiveTab() {
  const { chart } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [listSize, setListSize] = useState(50);

  function load() {
    setLoading(true);
    setError(null);
    api.predictive()
      .then((payload) => {
        setData(payload);
        const available = payload?.outreach?.customers?.length || 0;
        setListSize(Math.min(50, Math.max(1, available)));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  const meta = data?.meta || {};
  const leaderboard = data?.leaderboard || [];
  const curves = data?.curves || { x: [], roc: {}, pr: {} };
  const confusion = data?.confusion_matrix || {};
  const importance = (data?.feature_importance || []).slice(0, 10);
  const spend = data?.spend_model || {};
  const outreach = data?.outreach || { customers: [] };
  const customers = outreach.customers || [];
  const totalCustomers = outreach.total_customers || 0;

  const colors = chart.series;
  const modelNames = leaderboard.map((row) => row.model);

  const curveRows = useMemo(() => {
    if (!curves.x?.length) return [];
    return curves.x.map((xValue, index) => {
      const row = { x: xValue };
      modelNames.forEach((name) => {
        row[name] = curves.roc?.[name]?.[index] ?? null;
      });
      return row;
    });
  }, [curves, modelNames]);

  const prRows = useMemo(() => {
    if (!curves.x?.length) return [];
    return curves.x.map((xValue, index) => {
      const row = { x: xValue };
      modelNames.forEach((name) => {
        row[name] = curves.pr?.[name]?.[index] ?? null;
      });
      return row;
    });
  }, [curves, modelNames]);

  const visibleCustomers = customers.slice(0, listSize);
  const coveredShare = listSize > 0 ? customers[listSize - 1]?.cumulative_share_pct ?? 0 : 0;
  const coveredRevenue = visibleCustomers.reduce((sum, row) => sum + (row.expected_revenue_at_risk || 0), 0);

  const bestRow = leaderboard.find((row) => row.model === meta.best_model) || {};
  const cmTotal = (confusion.tp || 0) + (confusion.fp || 0) + (confusion.fn || 0) + (confusion.tn || 0);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={110} />)}
        </div>
        <Skeleton h={280} />
        <Skeleton h={280} />
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={load} />;
  }

  if (data?.status !== 'ok') {
    return (
      <div className="glass-card p-6 space-y-3">
        <h2 className="font-bold text-white">Predictive analytics unavailable for this dataset</h2>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{data?.message || 'Not enough history to build snapshots.'}</p>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          The model needs a 90-day feature window, a 90-day gap so training labels never overlap the
          test window, a 90-day outcome window, and two training cutoffs spaced 30 days apart. Load
          the full Online Retail dataset to see the evaluation.
        </p>
        <button onClick={load} className="download-btn" type="button">Retry</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Snapshot test cutoff <strong className="text-white">{meta.test_cutoff}</strong> · trained on{' '}
          {meta.train_cutoffs?.join(' and ')} · {meta.n_test_customers?.toLocaleString()} customers scored.
          Every training label window ends on or before the test cutoff, so no training label covers the
          test period. Built on the full loaded dataset; the header date/country filters do not apply here.
        </p>
        <div className="flex gap-2">
          <button onClick={load} className="download-btn" type="button" style={{ background: 'transparent' }}>↻ Refresh</button>
          <DownloadButton href={api.exportUrl('outreach')} label="Export outreach list" />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card">
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Best model ROC-AUC</p>
          <p className="text-2xl font-extrabold" style={{ color: 'var(--positive)' }}>{bestRow.roc_auc?.toFixed(3) ?? '—'}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{meta.best_model}</p>
        </div>
        <div className="kpi-card">
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Observed inactivity rate</p>
          <p className="text-2xl font-extrabold text-white">{fmtPct((meta.test_churn_rate || 0) * 100)}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Next {meta.horizon_days} days at test cutoff</p>
        </div>
        <div className="kpi-card">
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Top-decile lift</p>
          <p className="text-2xl font-extrabold text-white">{bestRow.top_decile_lift ? `${bestRow.top_decile_lift.toFixed(2)}×` : '—'}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>vs {fmtPct((meta.test_churn_rate || 0) * 100)} base rate</p>
        </div>
        <div className="kpi-card">
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Expected revenue at risk</p>
          <p className="text-2xl font-extrabold" style={{ color: 'var(--accent-red)' }}>{fmt(outreach.total_expected_at_risk, '£')}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Σ P(inactive) × predicted spend</p>
        </div>
      </div>

      <ChartCard title="Model leaderboard (held-out test cutoff)">
        <div style={{ overflowX: 'auto' }}>
          <div style={{ minWidth: 460 }}>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={leaderboard} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
                <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis type="category" dataKey="model" width={175} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip content={<CustomTooltip formatter={(v) => Number(v).toFixed(3)} />} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="roc_auc" name="ROC-AUC" fill={chart.bar} radius={[0, 3, 3, 0]} />
                <Bar dataKey="pr_auc" name="PR-AUC" fill={chart.barAlt} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <p style={captionStyle}>
          ROC-AUC measures how well each model ranks customers by risk (0.5 = coin flip). PR-AUC is
          the stricter score when only ~{fmtPct((meta.test_churn_rate || 0) * 100)} of customers actually
          go quiet. The dummy and the existing decline heuristic are included so any gain is visible.
        </p>
        <div className="overflow-auto mt-4" style={{ maxHeight: 240 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>ROC-AUC</th>
                <th>PR-AUC</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Lift (top 10%)</th>
                <th>Threshold</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row) => (
                <tr key={row.model}>
                  <td>
                    {row.model}
                    {row.is_baseline && <span className="text-xs" style={{ color: 'var(--text-muted)' }}> · baseline</span>}
                    {row.model === meta.best_model && <span className="text-xs" style={{ color: 'var(--positive)' }}> · selected</span>}
                  </td>
                  <td>{row.roc_auc?.toFixed(3) ?? '—'}</td>
                  <td>{row.pr_auc?.toFixed(3) ?? '—'}</td>
                  <td>{row.precision?.toFixed(3) ?? '—'}</td>
                  <td>{row.recall?.toFixed(3) ?? '—'}</td>
                  <td>{row.f1?.toFixed(3) ?? '—'}</td>
                  <td>{row.top_decile_lift ? `${row.top_decile_lift.toFixed(2)}×` : '—'}</td>
                  <td>{row.threshold?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={captionStyle}>
          Every threshold — and the choice of the selected model itself — used a 30% validation split of
          the training cutoffs, then each model was refit on all training snapshots and scored once on the
          test cutoff. The test set never influenced a threshold or the selection, so a model can rank
          differently here than the order in which models were chosen.
        </p>
      </ChartCard>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <ChartCard title="ROC curves (all models)">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={curveRows} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
              <XAxis dataKey="x" type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => v.toFixed(1)} label={{ value: 'False positive rate', position: 'insideBottom', offset: -4, fontSize: 10, fill: 'var(--text-muted)' }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
              <Tooltip content={<CustomTooltip formatter={(v) => Number(v).toFixed(3)} />} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {modelNames.map((name, index) => (
                <Line key={name} type="monotone" dataKey={name} stroke={colors[index % colors.length]} dot={false} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <p style={captionStyle}>
            Further toward the top-left is better. The diagonal is random guessing; the gap between the
            learned curves and the decline-rule curve is the value the supervised model adds.
          </p>
        </ChartCard>

        <ChartCard title="Precision–recall curves">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={prRows} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
              <XAxis dataKey="x" type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickFormatter={(v) => v.toFixed(1)} label={{ value: 'Recall', position: 'insideBottom', offset: -4, fontSize: 10, fill: 'var(--text-muted)' }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
              <Tooltip content={<CustomTooltip formatter={(v) => Number(v).toFixed(3)} />} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {modelNames.map((name, index) => (
                <Line key={name} type="monotone" dataKey={name} stroke={colors[index % colors.length]} dot={false} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <p style={captionStyle}>
            Precision = share of flagged customers who really did go quiet. The horizontal line a model
            must clear is the base inactivity rate of {fmtPct((meta.test_churn_rate || 0) * 100)}.
          </p>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <ChartCard title={`Confusion matrix — ${meta.best_model} @ ${meta.best_threshold?.toFixed(2)}`}>
          <div className="grid grid-cols-2 gap-3">
            {[
              { key: 'tp', label: 'True positives', hint: 'Flagged, went quiet', color: chart.positive },
              { key: 'fp', label: 'False positives', hint: 'Flagged, stayed active', color: chart.drop },
              { key: 'fn', label: 'False negatives', hint: 'Missed churners', color: chart.surge },
              { key: 'tn', label: 'True negatives', hint: 'Correctly left alone', color: chart.bar },
            ].map((cell) => (
              <div key={cell.key} className="p-4 rounded-xl" style={{ border: `1px solid ${cell.color}40`, background: `${cell.color}14` }}>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{cell.label}</p>
                <p className="text-2xl font-extrabold text-white">{confusion[cell.key] ?? 0}</p>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {cmTotal ? fmtPct(((confusion[cell.key] || 0) / cmTotal) * 100) : '—'} · {cell.hint}
                </p>
              </div>
            ))}
          </div>
          <p style={captionStyle}>
            At the threshold chosen on validation, the model flags {confusion.tp + confusion.fp || 0}{' '}
            customers, of which {confusion.tp || 0} really do stop buying. Precision{' '}
            {bestRow.precision?.toFixed(2) ?? '—'}, recall {bestRow.recall?.toFixed(2) ?? '—'}.
          </p>
        </ChartCard>

        <ChartCard title="What drives inactivity (permutation importance)">
          {importance.length === 0 ? (
            <p className="text-sm py-8 text-center" style={{ color: 'var(--text-muted)' }}>
              Importance unavailable for this split.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <div style={{ minWidth: 460 }}>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={[...importance].reverse()} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                    <YAxis
                      type="category"
                      dataKey="feature"
                      width={175}
                      tick={{ fontSize: 9, fill: 'var(--text-muted)' }}
                      tickFormatter={(value) => FEATURE_LABELS[value] || value}
                    />
                    <Tooltip content={<CustomTooltip formatter={(v) => Number(v).toFixed(3)} />} />
                    <Bar dataKey="importance" name="AUC drop" fill={chart.bar} radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
          <p style={captionStyle}>
            How much test ROC-AUC falls when a feature is shuffled, so taller bars are the signals the
            model actually relies on. This is association inside one dataset, not proof of causation.
          </p>
        </ChartCard>
      </div>

      <ChartCard title="Spend forecast (feeds the revenue-at-risk column)">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Model MAE</p>
            <p className="text-xl font-bold text-white">{fmt(Math.round(spend.mae_currency || 0), '£')}</p>
          </div>
          <div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Same-as-last-90d MAE</p>
            <p className="text-xl font-bold text-white">{fmt(Math.round(spend.baseline_mae_currency || 0), '£')}</p>
          </div>
          <div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Spearman (model)</p>
            <p className="text-xl font-bold" style={{ color: 'var(--positive)' }}>{spend.spearman?.toFixed(3) ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Spearman (baseline)</p>
            <p className="text-xl font-bold text-white">{spend.baseline_spearman?.toFixed(3) ?? '—'}</p>
          </div>
        </div>
        <p style={captionStyle}>
          {spend.model} predicts spend in the next {meta.horizon_days} days.{' '}
          {spend.skill_vs_baseline_pct != null && spend.skill_vs_baseline_pct >= 0
            ? `It beats the "assume they repeat the last 90 days" baseline by ${spend.skill_vs_baseline_pct.toFixed(1)}% MAE.`
            : `It does not beat the "assume they repeat the last 90 days" baseline on MAE (${Math.abs(spend.skill_vs_baseline_pct ?? 0).toFixed(1)}% worse).`}{' '}
          Its Spearman correlation ({spend.spearman?.toFixed(2) ?? '—'}) is{' '}
          {spend.spearman != null && spend.baseline_spearman != null && spend.spearman > spend.baseline_spearman ? 'higher' : 'not higher'}{' '}
          than the baseline&apos;s ({spend.baseline_spearman?.toFixed(2) ?? '—'}), which is why this forecast is
          used only to weight the outreach list, not reported as a revenue forecast.
        </p>
      </ChartCard>

      <ChartCard
        title="Outreach priority list"
        action={<DownloadButton href={api.exportUrl('outreach')} label={`Export all ${totalCustomers.toLocaleString()}`} />}
      >
        <div className="flex flex-col md:flex-row md:items-center gap-4 mb-5">
          <div className="flex-1">
            <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Customers to contact: {listSize}
            </label>
            <input
              type="range"
              min={1}
              max={Math.max(1, customers.length)}
              step={1}
              value={listSize}
              onChange={(e) => setListSize(Number(e.target.value))}
              className="w-full mt-2"
              style={{ accentColor: 'var(--link)' }}
            />
          </div>
          <div className="flex gap-6">
            <div>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Revenue at risk covered</p>
              <p className="text-lg font-bold" style={{ color: 'var(--accent-red)' }}>{fmt(coveredRevenue, '£')}</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Share of total</p>
              <p className="text-lg font-bold text-white">{fmtPct(coveredShare)}</p>
            </div>
          </div>
        </div>

        <div className="overflow-auto" style={{ maxHeight: 380 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Customer</th>
                <th>P(inactive)</th>
                <th>Predicted 90d spend</th>
                <th>Expected at risk</th>
                <th>Cumulative share</th>
                <th>Recency</th>
                <th>Orders (90d)</th>
              </tr>
            </thead>
            <tbody>
              {visibleCustomers.map((row) => (
                <tr key={row.CustomerID}>
                  <td>{row.rank}</td>
                  <td style={{ fontFamily: 'monospace' }}>{row.CustomerID}</td>
                  <td style={{ color: row.churn_probability >= 0.5 ? 'var(--accent-red)' : undefined }}>
                    {(row.churn_probability * 100).toFixed(1)}%
                  </td>
                  <td>{fmt(row.predicted_spend_90d, '£')}</td>
                  <td style={{ color: 'var(--accent-red)' }}>{fmt(row.expected_revenue_at_risk, '£')}</td>
                  <td>{fmtPct(row.cumulative_share_pct)}</td>
                  <td>{Math.round(row.recency_days)}d</td>
                  <td>{row.orders_lookback}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={captionStyle}>
          Expected revenue at risk = P(inactive) × predicted spend for the next {meta.horizon_days} days.
          The list is ranked by that value, so the slider answers &quot;how much of the exposure can we
          cover with N phone calls&quot;. The export always contains every scored customer.
        </p>
      </ChartCard>

    </div>
  );
}
