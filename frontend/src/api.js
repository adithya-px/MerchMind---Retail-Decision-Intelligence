const API_BASE = import.meta.env.VITE_API_URL ?? '';

function formatDetail(detail, fallback) {
  if (detail == null) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.detail || JSON.stringify(item)).join('; ');
  }
  return String(detail);
}

async function request(path, options = {}) {
  const { headers, body, ...rest } = options;
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(body && !isForm ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body,
    ...rest,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(formatDetail(err.detail, `Request failed: ${res.status}`));
  }
  return res.json();
}

function buildQuery(params = {}) {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '' || value === 'All') continue;
    q.set(key, value);
  }
  const serialized = q.toString();
  return serialized ? `?${serialized}` : '';
}

export const api = {
  health: () => request('/api/health'),
  datasetStatus: () => request('/api/dataset/status'),
  uploadDataset: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/api/dataset/upload', { method: 'POST', body: form });
  },
  loadDemo: () => request('/api/dataset/demo', { method: 'POST' }),
  resetDataset: () => request('/api/dataset/reset', { method: 'POST' }),
  overview: (filters) => request(`/api/overview${buildQuery(filters)}`),
  sales: (filters) => request(`/api/sales${buildQuery(filters)}`),
  customerSegments: (filters) => request(`/api/customer-segments${buildQuery(filters)}`),
  modelDiagnostics: (filters) => request(`/api/model-diagnostics${buildQuery(filters)}`),
  decliningCustomers: (filters) => request(`/api/declining-customers${buildQuery(filters)}`),
  recommendations: (filters) => request(`/api/recommendations${buildQuery(filters)}`),
  anomalies: (filters) => request(`/api/anomalies${buildQuery(filters)}`),
  auditLog: () => request('/api/audit-log'),
  exportUrl: (type, filters = {}, extra = {}) =>
    `${API_BASE}/api/export/${type}${buildQuery({ ...filters, ...extra })}`,
};
