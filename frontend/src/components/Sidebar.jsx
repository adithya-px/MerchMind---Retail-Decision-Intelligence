import { useState } from 'react';
import { LayoutDashboard, TrendingUp, Users, Zap, AlertTriangle, Star, ClipboardList, Download, ChevronDown, Upload, Sparkles } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
  { id: 'sales', icon: TrendingUp, label: 'Sales Analytics' },
  { id: 'segments', icon: Users, label: 'Segments' },
  { id: 'anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { id: 'declining', icon: Zap, label: 'At-Risk' },
  { id: 'recommendations', icon: Star, label: 'Recommendations' },
  { id: 'audit', icon: ClipboardList, label: 'Audit Log' },
  { id: 'exports', icon: Download, label: 'Exports' },
];

export default function Sidebar({ activeTab, onTabChange, datasetInfo, onReset }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className="flex flex-col h-full transition-all duration-300"
      style={{
        width: collapsed ? 64 : 220,
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-dim)',
        flexShrink: 0,
      }}>
      {/* Brand */}
      <div className="flex items-center gap-3 p-4" style={{ borderBottom: '1px solid var(--border-dim)', minHeight: 64 }}>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #38bdf8, #818cf8)' }}>
          <Sparkles size={18} color="#fff" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="font-bold text-sm text-white truncate leading-tight">MerchMind</p>
            <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>Analytics</p>
          </div>
        )}
      </div>

      {/* Dataset Badge */}
      {!collapsed && datasetInfo && (
        <div className="mx-3 my-3 p-3 rounded-xl" style={{ background: 'rgba(56,189,248,0.07)', border: '1px solid var(--border-accent)' }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="status-dot active" />
            <span className="text-xs font-semibold" style={{ color: 'var(--accent-cyan)' }}>Dataset Active</span>
          </div>
          <p className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>{datasetInfo.filename}</p>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{datasetInfo.rows?.toLocaleString()} rows</p>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ id, icon: Icon, label }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className="w-full flex items-center gap-3 rounded-xl transition-all duration-150"
              style={{
                padding: collapsed ? '10px' : '10px 12px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active ? 'rgba(56,189,248,0.12)' : 'transparent',
                color: active ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: active ? '1px solid var(--border-accent)' : '1px solid transparent',
                fontWeight: active ? 600 : 500,
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
              title={collapsed ? label : ''}
            >
              <Icon size={18} style={{ flexShrink: 0 }} />
              {!collapsed && <span className="truncate">{label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Footer actions */}
      <div className="p-3 space-y-1" style={{ borderTop: '1px solid var(--border-dim)' }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center gap-3 rounded-xl transition-all"
          style={{
            padding: collapsed ? '10px' : '10px 12px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            background: 'transparent',
            color: 'var(--text-muted)',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          <ChevronDown size={16} style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(90deg)', transition: 'transform 0.2s' }} />
          {!collapsed && <span>Collapse</span>}
        </button>
        <button
          onClick={onReset}
          className="w-full flex items-center gap-3 rounded-xl transition-all"
          style={{
            padding: collapsed ? '10px' : '10px 12px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            background: 'transparent',
            color: 'var(--text-muted)',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
          title="Upload new dataset"
        >
          <Upload size={16} />
          {!collapsed && <span>New Dataset</span>}
        </button>
      </div>
    </aside>
  );
}
