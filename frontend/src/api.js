const API_BASE = process.env.REACT_APP_API_URL || '';
function getToken() { return localStorage.getItem('server_stats_token'); }
function setToken(token) { localStorage.setItem('server_stats_token', token); }
function getMasterKey() { return process.env.REACT_APP_API_KEY || ''; }
function clearToken() { localStorage.removeItem('server_stats_token'); localStorage.removeItem('server_stats_user'); }
function getStoredUser() { const stored = localStorage.getItem('server_stats_user'); return stored ? JSON.parse(stored) : null; }
function storeUser(user) { localStorage.setItem('server_stats_user', JSON.stringify(user)); }

async function request(endpoint, options = {}) {
  const token = getToken();
  const masterKey = getMasterKey();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (masterKey) headers['X-API-Key'] = masterKey;
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (res.status === 401) { clearToken(); window.location.hash = '#/login'; throw new Error('Session expired'); }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `API error: ${res.status}`); }
  return res.json();
}

// Auth
export async function login(username, password) { const data = await request('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); setToken(data.access_token); storeUser(data.user); return data; }
export async function register(username, email, password) { const data = await request('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) }); setToken(data.access_token); storeUser(data.user); return data; }
export async function seedAdmin() { return request('/api/auth/admin/seed', { method: 'POST', body: '{}' }); }
export function logout() { clearToken(); }
export function isAuthenticated() { return !!getToken() || !!getMasterKey(); }
export function getCurrentUser() { return getStoredUser(); }
export function getStats() { return request('/api/stats'); }
export function getLatestStats() { return request('/api/stats/latest'); }
export function getHistory(period = '1h') { return request(`/api/stats/history?period=${period}`); }
export function getHealth() { return request('/api/health'); }
export function getConfig() { return request('/api/config'); }
export function listApiKeys() { return request('/api/auth/api-keys'); }
export function createApiKey(name = 'default') { return request('/api/auth/api-keys', { method: 'POST', body: JSON.stringify({ name }) }); }
export function deleteApiKey(keyId) { return request(`/api/auth/api-keys/${keyId}`, { method: 'DELETE' }); }
export function getTrafficLive() { return request('/traffic/live'); }
export function getTrafficHistory(period = '1h') { return request(`/traffic/history?period=${period}`); }
export function listUsers() { return request('/api/auth/admin/users'); }
export function approveUser(userId) { return request(`/api/auth/admin/users/${userId}/approve`, { method: 'POST' }); }
export function rejectUser(userId) { return request(`/api/auth/admin/users/${userId}/reject`, { method: 'POST' }); }
export function makeAdmin(userId) { return request(`/api/auth/admin/users/${userId}/make-admin`, { method: 'POST' }); }

// Metrics
export function getMetricsCurrent() { return request('/metrics/current'); }
export function getMetricsHistory(period = '1h') { return request(`/metrics/history?period=${period}`); }
export function getNetworkDeep() { return request('/metrics/network/deep'); }
export function getDiskIOPS() { return request('/metrics/disk/iops'); }

// IP Reputation
export function getIPReputation(ip) { return request(`/ip/${ip}`); }
export function forceCheckIP(ip) { return request(`/ip/check/${ip}`); }
export function getTopMaliciousIPs(limit = 20) { return request(`/ip/top-malicious?limit=${limit}`); }
export function getIPReputationStats() { return request('/ip/stats'); }
export function batchCheckIPs(ips) { return request('/ip/batch-check', { method: 'POST', body: JSON.stringify({ ips }) }); }

// ── ALERT MANAGER ─────────────────────────────────────────────────
export function getAlertRules() { return request('/alerts/rules'); }
export function createAlertRule(data) { return request('/alerts/rules', { method: 'POST', body: JSON.stringify(data) }); }
export function updateAlertRule(id, data) { return request(`/alerts/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
export function deleteAlertRule(id) { return request(`/alerts/rules/${id}`, { method: 'DELETE' }); }
export function getActiveAlerts(limit = 50) { return request(`/alerts/active?limit=${limit}`); }
export function getAlertHistory(limit = 100, status) { return request(`/alerts/history?limit=${limit}${status ? `&status=${status}` : ''}`); }
export function acknowledgeAlert(id, username) { return request(`/alerts/${id}/acknowledge`, { method: 'POST', body: JSON.stringify({ username }) }); }
export function resolveAlert(id, username) { return request(`/alerts/${id}/resolve`, { method: 'POST', body: JSON.stringify({ username }) }); }
export function getAlertChannels() { return request('/alerts/channels'); }
export function createAlertChannel(data) { return request('/alerts/channels', { method: 'POST', body: JSON.stringify(data) }); }
export function deleteAlertChannel(id) { return request(`/alerts/channels/${id}`, { method: 'DELETE' }); }
export function testAlertChannel(id) { return request(`/alerts/channels/${id}/test`, { method: 'POST' }); }

// ── SERVERS ───────────────────────────────────────────────────────
export function getServers() { return request('/servers'); }
export function getServerSummary() { return request('/servers/summary'); }
export function registerServer(data) { return request('/servers/register', { method: 'POST', body: JSON.stringify(data) }); }
export function getServer(id) { return request(`/servers/${id}`); }
export function deleteServer(id) { return request(`/servers/${id}`, { method: 'DELETE' }); }

// ── UPTIME MONITOR ────────────────────────────────────────────────
export function getUptimeMonitors() { return request('/uptime/monitors'); }
export function createUptimeMonitor(data) { return request('/uptime/monitors', { method: 'POST', body: JSON.stringify(data) }); }
export function updateUptimeMonitor(id, data) { return request(`/uptime/monitors/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
export function deleteUptimeMonitor(id) { return request(`/uptime/monitors/${id}`, { method: 'DELETE' }); }
export function checkUptimeNow(id) { return request(`/uptime/monitors/${id}/check`, { method: 'POST' }); }
export function getUptimeHistory(id, hours = 24) { return request(`/uptime/monitors/${id}/history?hours=${hours}`); }
export function getUptimeIncidents(id) { return request(`/uptime/monitors/${id}/incidents`); }

// ── SSL ───────────────────────────────────────────────────────────
export function scanSSL(hostname, port = 443) { return request('/ssl/scan', { method: 'POST', body: JSON.stringify({ hostname, port }) }); }
export function getSSLCertificates() { return request('/ssl/certificates'); }
export function getSSLCertificate(id) { return request(`/ssl/certificates/${id}`); }
export function deleteSSLCertificate(id) { return request(`/ssl/certificates/${id}`, { method: 'DELETE' }); }

// ── PROCESS MONITOR ───────────────────────────────────────────────
export function getMonitoredProcesses() { return request('/processes'); }
export function createMonitoredProcess(data) { return request('/processes', { method: 'POST', body: JSON.stringify(data) }); }
export function deleteMonitoredProcess(id) { return request(`/processes/${id}`, { method: 'DELETE' }); }
export function checkMonitoredProcess(id) { return request(`/processes/${id}/check`, { method: 'POST' }); }
export function checkAllProcesses() { return request('/processes/check-all', { method: 'POST' }); }
export function getProcessEvents(id, limit = 50) { return request(`/processes/${id}/events?limit=${limit}`); }
