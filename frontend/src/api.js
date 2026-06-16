const API_BASE = process.env.REACT_APP_API_URL || '';

// Token management
function getToken() {
  return localStorage.getItem('server_stats_token');
}

function setToken(token) {
  localStorage.setItem('server_stats_token', token);
}

function getMasterKey() {
  return process.env.REACT_APP_API_KEY || '';
}

function clearToken() {
  localStorage.removeItem('server_stats_token');
  localStorage.removeItem('server_stats_user');
}

function getStoredUser() {
  const stored = localStorage.getItem('server_stats_user');
  return stored ? JSON.parse(stored) : null;
}

function storeUser(user) {
  localStorage.setItem('server_stats_user', JSON.stringify(user));
}

async function request(endpoint, options = {}) {
  const token = getToken();
  const masterKey = getMasterKey();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Try JWT token first, fall back to master API key
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (masterKey) {
    headers['X-API-Key'] = masterKey;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Token expired or invalid — clear and redirect
    clearToken();
    window.location.hash = '#/login';
    throw new Error('Session expired. Please log in again.');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ── Auth API ──────────────────────────────────────────────────────────

export async function login(username, password) {
  const data = await request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  storeUser(data.user);
  return data;
}

export async function register(username, email, password) {
  const data = await request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
  setToken(data.access_token);
  storeUser(data.user);
  return data;
}

export async function seedAdmin(password) {
  const data = await request('/api/auth/admin/seed', {
    method: 'POST',
    body: JSON.stringify({}),
  });
  return data;
}

export function logout() {
  clearToken();
}

export function isAuthenticated() {
  return !!getToken() || !!getMasterKey();
}

export function getCurrentUser() {
  return getStoredUser();
}

// ── Stats API ─────────────────────────────────────────────────────────

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

// ── API Key Management ────────────────────────────────────────────────

export function listApiKeys() {
  return request('/api/auth/api-keys');
}

export function createApiKey(name = 'default') {
  return request('/api/auth/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function deleteApiKey(keyId) {
  return request(`/api/auth/api-keys/${keyId}`, {
    method: 'DELETE',
  });
}

// ── Admin: User Management ─────────────────────────────────────────

export function listUsers() {
  return request('/api/auth/admin/users');
}

export function approveUser(userId) {
  return request(`/api/auth/admin/users/${userId}/approve`, { method: 'POST' });
}

export function rejectUser(userId) {
  return request(`/api/auth/admin/users/${userId}/reject`, { method: 'POST' });
}

export function makeAdmin(userId) {
  return request(`/api/auth/admin/users/${userId}/make-admin`, { method: 'POST' });
}
