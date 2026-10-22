import { useCallback, useRef, useState } from 'react';
import { Upload, FileSpreadsheet, Sparkles, AlertCircle } from 'lucide-react';
import { api } from '../api';
import { Loader } from './ui';
import ThemeToggle from './ThemeToggle';

export default function DataUpload({ onDatasetLoaded }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef();

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      setError('Please upload a CSV or Excel (.xlsx/.xls) file.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const result = await api.uploadDataset(file);
      onDatasetLoaded(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [onDatasetLoaded]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }, [handleFile]);

  const handleDemo = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const result = await api.loadDemo();
      onDatasetLoaded(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [onDatasetLoaded]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative" style={{ background: 'var(--bg-primary)' }}>
      {/* Theme switch */}
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      {/* Logo / Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))' }}>
            <Sparkles size={24} color="#fff" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">MerchMind</h1>
            <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Customer Analytics Dashboard</p>
          </div>
        </div>
        <h2 className="text-3xl font-extrabold text-white mb-2">Load Your Dataset</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 480, margin: '0 auto', lineHeight: 1.6 }}>
          Upload a retail transaction file to generate insights — KPIs, sales trends, and customer segments.
        </p>
      </div>

      <div className="w-full max-w-lg space-y-4">
        {/* Upload Zone */}
        <div
          className={`upload-zone ${dragging ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !loading && inputRef.current?.click()}
          style={{ cursor: loading ? 'wait' : 'pointer' }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {loading ? (
            <Loader label="Processing dataset…" />
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-full flex items-center justify-center" style={{ background: 'color-mix(in srgb, var(--accent-cyan) 14%, transparent)' }}>
                <Upload size={26} style={{ color: 'var(--accent-cyan)' }} />
              </div>
              <div>
                <p className="font-semibold text-white mb-1">Drag & drop or click to upload</p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Accepts CSV, XLSX, XLS</p>
              </div>
            </div>
          )}
        </div>

        {/* Required columns hint */}
        <div className="glass-card p-4">
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>Required Columns</p>
          <div className="flex flex-wrap gap-2">
            {['InvoiceNo','StockCode','Description','Quantity','InvoiceDate','UnitPrice','CustomerID','Country'].map(col => (
              <span key={col} className="text-xs px-2 py-1 rounded" style={{ background: 'var(--bg-elevated)', color: 'var(--link)', fontFamily: 'monospace' }}>{col}</span>
            ))}
          </div>
        </div>

        {/* Demo data */}
        <div className="text-center">
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No file? &nbsp;</span>
          <button
            onClick={handleDemo}
            disabled={loading}
            className="font-semibold text-sm transition-colors"
            style={{ color: 'var(--link)', background: 'none', border: 'none', cursor: loading ? 'wait' : 'pointer', textDecoration: 'underline' }}
          >
            <FileSpreadsheet size={14} style={{ display: 'inline', marginRight: 4 }} />
            Load demo dataset
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 p-4 rounded-xl" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
            <AlertCircle size={16} style={{ color: 'var(--accent-red)', flexShrink: 0, marginTop: 2 }} />
            <p className="text-sm" style={{ color: 'var(--accent-red)' }}>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
