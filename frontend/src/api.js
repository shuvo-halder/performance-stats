const API_BASE = process.env.REACT_APP_API_URL || '';
const API_KEY = process.env.REACT_APP_API_KEY || 'sk-prod-server-stats-monitor-key-2026';

async function request(endpoint) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getStats() {
  return request('/api/stats');
}

export function getLatestStats() {
  return request('/api/stats/latest');
}

export function getHistory(period = '1h') {
  return request(`/api/stats/history?period=${period}`);
}

export function getHealth() {
  return request('/api/health');
}

export function getConfig() {
  return request('/api/config');
}