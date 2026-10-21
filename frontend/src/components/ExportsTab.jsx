import { api } from '../api';
import { DownloadButton } from './ui';

const EXPORTS = [
  { type: 'sales', label: 'Cleaned positive transactions', detail: 'Line-level sales after the audit-logged cleaning pipeline, filtered to the active date and country cohort.' },
  { type: 'monthly', label: 'Monthly sales summary', detail: 'Positive sales value, order counts, and month-over-month growth for the active filters.' },
  { type: 'segments', label: 'RFM + K-Means segments', detail: 'Identified-customer RFM table with cluster labels from the currently selected k.' },
  { type: 'declining', label: 'Declining-activity accounts', detail: 'Heuristic spend-drop and cadence-lapse flags, ranked by revenue at risk.' },
  { type: 'anomalies', label: 'Daily sales anomalies', detail: 'Days that breached the rolling median / IQR envelope.' },
];

export default function ExportsTab({ filters, k }) {
  return (
    <div className="space-y-4">
      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        Downloads use the same date range, country filter, and cluster count currently applied in the header. Values are computed from the loaded dataset, not placeholders.
      </p>
      {EXPORTS.map((item) => (
        <div key={item.type} className="glass-card p-5 flex flex-wrap gap-3 items-center">
          <div className="flex-1 min-w-[220px]">
            <h3 className="font-semibold text-white">{item.label}</h3>
            <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{item.detail}</p>
          </div>
          <DownloadButton href={api.exportUrl(item.type, filters, { k })} label="Download CSV" />
        </div>
      ))}
    </div>
  );
}
