import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api';
import DataUpload from './components/DataUpload';
import Sidebar from './components/Sidebar';
import OverviewTab from './components/OverviewTab';
import SalesTab from './components/SalesTab';
import SegmentsTab from './components/SegmentsTab';
import AnomaliesTab from './components/AnomaliesTab';
import DecliningTab from './components/DecliningTab';
import PredictiveTab from './components/PredictiveTab';
import RecommendationsTab from './components/RecommendationsTab';
import AuditTab from './components/AuditTab';
import ExportsTab from './components/ExportsTab';
import ThemeToggle from './components/ThemeToggle';
import { ErrorBanner, FilterSelect, Loader } from './components/ui';

const TABS = {
  overview: OverviewTab,
  sales: SalesTab,
  segments: SegmentsTab,
  anomalies: AnomaliesTab,
  declining: DecliningTab,
  predictive: PredictiveTab,
  recommendations: RecommendationsTab,
  audit: AuditTab,
  exports: ExportsTab,
};

function emptyFilters(dataset) {
  return {
    start_date: dataset?.min_date || '',
    end_date: dataset?.max_date || '',
    countries: 'All',
    k: 4,
  };
}

export default function App() {
  const [dataset, setDataset] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [bootError, setBootError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [filters, setFilters] = useState(emptyFilters());

  const refreshStatus = useCallback(async () => {
    const status = await api.datasetStatus();
    setDataset(status);
    if (status.loaded) {
      setFilters((prev) => ({
        ...prev,
        start_date: prev.start_date || status.min_date || '',
        end_date: prev.end_date || status.max_date || '',
      }));
    }
    return status;
  }, []);

  useEffect(() => {
    refreshStatus()
      .catch((err) => setBootError(err.message))
      .finally(() => setBootstrapping(false));
  }, [refreshStatus]);

  const handleDatasetLoaded = useCallback((status) => {
    setDataset(status);
    setFilters(emptyFilters(status));
    setActiveTab('overview');
  }, []);

  const handleReset = useCallback(async () => {
    try {
      await api.resetDataset();
    } catch {
      // Still return to upload even if reset fails (e.g. backend already empty).
    }
    setDataset({ loaded: false });
    setFilters(emptyFilters());
    setActiveTab('overview');
  }, []);

  const queryFilters = useMemo(() => ({
    start_date: filters.start_date,
    end_date: filters.end_date,
    countries: filters.countries,
  }), [filters.start_date, filters.end_date, filters.countries]);

  const countryOptions = useMemo(() => {
    const values = dataset?.countries || [];
    return values.includes('All') ? values : ['All', ...values];
  }, [dataset]);

  if (bootstrapping) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-primary)' }}>
        <Loader label="Connecting to MerchMind API…" />
      </div>
    );
  }

  if (bootError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-lg w-full">
          <ErrorBanner message={`Cannot reach the API. Start the backend on port 8000. ${bootError}`} onRetry={() => {
            setBootError(null);
            setBootstrapping(true);
            refreshStatus().catch((err) => setBootError(err.message)).finally(() => setBootstrapping(false));
          }} />
        </div>
      </div>
    );
  }

  if (!dataset?.loaded) {
    return <DataUpload onDatasetLoaded={handleDatasetLoaded} />;
  }

  const Tab = TABS[activeTab] || OverviewTab;

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        datasetInfo={{ filename: dataset.filename, rows: dataset.sales_rows }}
        onReset={handleReset}
      />
      <main className="flex-1 min-w-0 flex flex-col">
        <header className="px-4 md:px-6 py-4 flex flex-wrap gap-4 items-end" style={{ borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-secondary)' }}>
          <div className="mr-auto min-w-0">
            <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Active cohort</p>
            <h1 className="text-lg font-bold text-white truncate">{dataset.filename}</h1>
          </div>
          <ThemeToggle />
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Start</span>
            <input
              type="date"
              value={filters.start_date}
              min={dataset.min_date || undefined}
              max={dataset.max_date || undefined}
              onChange={(e) => setFilters((prev) => ({ ...prev, start_date: e.target.value }))}
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)', color: 'var(--text-primary)', borderRadius: 8, padding: '6px 10px' }}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>End</span>
            <input
              type="date"
              value={filters.end_date}
              min={dataset.min_date || undefined}
              max={dataset.max_date || undefined}
              onChange={(e) => setFilters((prev) => ({ ...prev, end_date: e.target.value }))}
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)', color: 'var(--text-primary)', borderRadius: 8, padding: '6px 10px' }}
            />
          </label>
          <FilterSelect
            label="Country"
            value={filters.countries}
            onChange={(value) => setFilters((prev) => ({ ...prev, countries: value }))}
            options={countryOptions}
          />
          {(activeTab === 'segments' || activeTab === 'recommendations' || activeTab === 'exports') && (
            <FilterSelect
              label="K clusters"
              value={String(filters.k)}
              onChange={(value) => setFilters((prev) => ({ ...prev, k: Number(value) }))}
              options={['2', '3', '4', '5', '6', '7', '8']}
            />
          )}
        </header>
        <section className="flex-1 p-4 md:p-6 overflow-auto">
          <Tab filters={queryFilters} k={filters.k} countries={countryOptions} />
        </section>
      </main>
    </div>
  );
}
