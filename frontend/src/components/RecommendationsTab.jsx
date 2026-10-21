import { useEffect, useState } from 'react';
import { api } from '../api';
import { ChartCard, ErrorBanner, Skeleton, SegmentBadge, fmt, fmtPct } from './ui';

export default function RecommendationsTab({ filters, k }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    api.recommendations({ ...filters, k })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [filters, k]);

  const playbooks = data?.playbooks || [];

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} onRetry={load} />}
      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        Playbooks are heuristic strategies derived from computed RFM cluster profiles. They are not causal predictions and should be validated with holdout tests.
      </p>
      {loading ? <Skeleton h={240} /> : playbooks.map((book) => (
        <ChartCard key={book.segment_name} title={book.strategy_type} action={<SegmentBadge segment={book.segment_name} />}>
          <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
            {fmt(book.customer_count)} customers · {fmtPct(book.revenue_share_pct)} revenue · avg recency {book.avg_recency?.toFixed?.(0)}d · avg spend {fmt(book.avg_monetary, '£')}
          </p>
          <p className="text-sm text-white mb-3">{book.objective}</p>
          <ul className="list-disc pl-5 space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {(book.actions || []).map((action) => <li key={action}>{action}</li>)}
          </ul>
        </ChartCard>
      ))}
    </div>
  );
}
