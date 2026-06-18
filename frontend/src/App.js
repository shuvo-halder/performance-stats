import React, { useState, useEffect, useCallback } from 'react';
import Login from './components/Login';
import AdminPanel from './components/AdminPanel';
import TrafficPanel from './components/TrafficPanel';
import ThreatPanel from './components/ThreatPanel';
import { getStats, getLatestStats, getHistory, getCurrentUser, isAuthenticated, logout } from './api';
import './styles/dashboard.css';

function Dashboard({ user, onLogout, onShowTraffic }) {
  const [showAdmin, setShowAdmin] = useState(false);
  const [data, setData] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [historyPeriod, setHistoryPeriod] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = useCallback(async (isBackground = false) => {
    try {
      // First load: show cached data instantly, then refresh
      if (!isBackground) {
        try {
          const latest = await getLatestStats();
          setData(latest);
          setError(null);
        } catch (_) {
          // No cached data yet, that's fine
        }
      }
      // Always fetch fresh data
      const stats = await getStats();
      setData(stats);
      setError(null);
    } catch (err) {
      if (!data) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [data]);

  const fetchHistory = useCallback(async () => {
    try {
      const h = await getHistory(historyPeriod);
      setHistory(h);
    } catch (err) {
      console.error('History fetch error:', err);
    }
  }, [historyPeriod]);

  useEffect(() => {
    fetchData();
    fetchHistory();
  }, [fetchData, fetchHistory]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchData(true);
      fetchHistory();
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData, fetchHistory]);

  useEffect(() => {
    fetchHistory();
  }, [historyPeriod, fetchHistory]);

  if (loading) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="spinner"></div>
          <p>Collecting system metrics...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="app">
        <div className="error-screen">
          <div className="error-icon">⚠️</div>
          <h2>Connection Error</h2>
          <p>{error}</p>
          <p className="error-hint">Make sure the API server is running and accessible.</p>
          <button onClick={fetchData} className="retry-btn">Retry</button>
        </div>
      </div>
    );
  }

  const cpuPercent = data?.cpu_usage_percent || 0;
  const memPercent = data?.mem_usage_percent || 0;
  const alerts = data?.alerts || [];

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1 className="header-title">🖥️ Server Monitor</h1>
          <span className="header-hostname">{data?.hostname || 'unknown'}</span>
        </div>
        <div className="header-right">
          <span className="header-user">👤 {user?.username || 'user'}</span>
          <span className="header-time">{data?.timestamp ? new Date(data.timestamp).toLocaleString() : ''}</span>
          <span className={`status-badge ${alerts.length === 0 ? 'healthy' : 'warning'}`}>
            {alerts.length === 0 ? '● Healthy' : `● ${alerts.length} Alert(s)`}
          </span>
          <label className="auto-refresh-toggle">
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
            <span className="toggle-label">Auto</span>
          </label>
          <button onClick={onShowTraffic} className="traffic-nav-btn" title="Traffic Monitor">🚦</button>
          {user?.is_admin && (
            <button onClick={() => setShowAdmin(true)} className="admin-btn" title="User Management">👥</button>
          )}
          <button onClick={onLogout} className="logout-btn" title="Sign out">🚪</button>
        </div>
      </header>

      <div className="alerts-bar">
        {alerts.length === 0 ? (
          <div className="alert-item alert-ok">✅ All systems within normal thresholds</div>
        ) : (
          alerts.map((alert, i) => (
            <div key={i} className={`alert-item alert-${alert.severity}`}>
              {alert.severity === 'critical' ? '🔴' : '🟡'} {alert.message}
            </div>
          ))
        )}
      </div>

      <div className="dashboard-grid">
        {/* CPU Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">🔲</span>
            <h2>CPU</h2>
          </div>
          <div className="card-body">
            <div className="gauge-container">
              <div className="gauge">
                <svg viewBox="0 0 120 120" className="gauge-svg">
                  <circle cx="60" cy="60" r="54" fill="none" stroke="#e2e8f0" strokeWidth="8" />
                  <circle
                    cx="60" cy="60" r="54"
                    fill="none"
                    stroke={cpuPercent > 80 ? '#ef4444' : cpuPercent > 60 ? '#f59e0b' : '#22c55e'}
                    strokeWidth="8"
                    strokeDasharray={`${(cpuPercent / 100) * 339.3} 339.3`}
                    strokeLinecap="round"
                    transform="rotate(-90 60 60)"
                  />
                </svg>
                <div className="gauge-value">{cpuPercent.toFixed(1)}%</div>
              </div>
              <div className="gauge-info">
                <div className="info-row"><span>Cores:</span><span>{data?.cpu_cores}</span></div>
                <div className="info-row"><span>Load 1m:</span><span>{data?.cpu_load_1min}</span></div>
                <div className="info-row"><span>Load 5m:</span><span>{data?.cpu_load_5min}</span></div>
                <div className="info-row"><span>Load 15m:</span><span>{data?.cpu_load_15min}</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Memory Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">🧠</span>
            <h2>Memory</h2>
          </div>
          <div className="card-body">
            <div className="progress-container">
              <div className="progress-bar-wrapper">
                <div className="progress-bar" style={{ width: `${memPercent}%`, backgroundColor: memPercent > 85 ? '#ef4444' : memPercent > 70 ? '#f59e0b' : '#3b82f6' }}></div>
              </div>
              <div className="progress-value">{memPercent.toFixed(1)}%</div>
            </div>
            <div className="memory-details">
              <div className="memory-item">
                <span className="mem-label">Total</span>
                <span className="mem-value">{data?.mem_total_mb?.toFixed(0)} MB</span>
              </div>
              <div className="memory-item">
                <span className="mem-label used">Used</span>
                <span className="mem-value">{data?.mem_used_mb?.toFixed(0)} MB</span>
              </div>
              <div className="memory-item">
                <span className="mem-label free">Free</span>
                <span className="mem-value">{data?.mem_free_mb?.toFixed(0)} MB</span>
              </div>
            </div>
          </div>
        </div>

        {/* System Info Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">ℹ️</span>
            <h2>System</h2>
          </div>
          <div className="card-body">
            <div className="sys-info">
              <div className="info-row"><span>OS:</span><span>{data?.os_name}</span></div>
              <div className="info-row"><span>Kernel:</span><span>{data?.kernel}</span></div>
              <div className="info-row"><span>Uptime:</span><span>{data?.uptime}</span></div>
              <div className="info-row"><span>Failed Logins:</span><span className={data?.failed_logins > 10 ? 'text-danger' : ''}>{data?.failed_logins}</span></div>
              <div className="info-row"><span>TCP Connections:</span><span>{data?.network_connections}</span></div>
            </div>
          </div>
        </div>

        {/* Disk Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">💾</span>
            <h2>Disk Usage</h2>
          </div>
          <div className="card-body">
            {data?.disk_data?.map((disk, i) => (
              <div key={i} className="disk-item">
                <div className="disk-header">
                  <span className="disk-mount">{disk.mount}</span>
                  <span className="disk-percent">{disk.usage_percent}%</span>
                </div>
                <div className="disk-bar-wrapper">
                  <div
                    className="disk-bar"
                    style={{
                      width: `${disk.usage_percent}%`,
                      backgroundColor: disk.usage_percent > 90 ? '#ef4444' : disk.usage_percent > 75 ? '#f59e0b' : '#22c55e'
                    }}
                  ></div>
                </div>
                <div className="disk-details">
                  <span>{disk.used_gb} GB / {disk.total_gb} GB</span>
                </div>
              </div>
            ))}
            {(!data?.disk_data || data.disk_data.length === 0) && <p className="no-data">No disk data available</p>}
          </div>
        </div>

        {/* Services Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">⚙️</span>
            <h2>Services</h2>
          </div>
          <div className="card-body">
            <div className="services-grid">
              {data?.services_data?.map((svc, i) => (
                <div key={i} className={`service-item ${svc.status === 'active' || svc.status === 'running' || svc.status === 'active (restarted)' ? 'running' : 'stopped'}`}>
                  <div className="service-name">{svc.name}</div>
                  <div className="service-status">
                    <span className={`status-dot ${svc.status === 'active' || svc.status === 'running' || svc.status === 'active (restarted)' ? 'green' : 'red'}`}></span>
                    {svc.status}
                  </div>
                </div>
              ))}
            </div>
            {data?.auto_restart_results?.length > 0 && (
              <div className="restart-results">
                <h4>Auto-Restart Results</h4>
                {data.auto_restart_results.map((r, i) => (
                  <div key={i} className={`restart-item ${r.restarted ? 'success' : 'failed'}`}>
                    {r.service}: {r.restarted ? '✅ Restarted' : '❌ Failed'}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Network Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">🌐</span>
            <h2>Network & Ports</h2>
          </div>
          <div className="card-body">
            <div className="info-row large"><span>Active TCP:</span><span className="big-number">{data?.network_connections}</span></div>
            <h4 className="section-title">Listening Ports</h4>
            {data?.network_listening_ports?.length > 0 ? (
              <div className="ports-table">
                <div className="ports-header">
                  <span>Port</span>
                  <span>Process</span>
                </div>
                {data.network_listening_ports.slice(0, 10).map((p, i) => (
                  <div key={i} className="ports-row">
                    <span className="port-num">{p.port}</span>
                    <span className="port-proc">{p.process}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No port data</p>
            )}
          </div>
        </div>

        {/* Top Processes Card */}
        <div className="card card-wide">
          <div className="card-header">
            <span className="card-icon">📊</span>
            <h2>Top Processes</h2>
          </div>
          <div className="card-body">
            <div className="processes-grid">
              <div className="process-column">
                <h4>🔥 Top CPU</h4>
                <div className="proc-table">
                  <div className="proc-header">
                    <span>PID</span>
                    <span>Name</span>
                    <span>CPU%</span>
                  </div>
                  {data?.top_cpu_processes?.map((p, i) => (
                    <div key={i} className="proc-row">
                      <span className="proc-pid">{p.pid}</span>
                      <span className="proc-name">{p.name}</span>
                      <span className="proc-value">{p.cpu_percent}%</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="process-column">
                <h4>💾 Top Memory</h4>
                <div className="proc-table">
                  <div className="proc-header">
                    <span>PID</span>
                    <span>Name</span>
                    <span>MEM%</span>
                  </div>
                  {data?.top_mem_processes?.map((p, i) => (
                    <div key={i} className="proc-row">
                      <span className="proc-pid">{p.pid}</span>
                      <span className="proc-name">{p.name}</span>
                      <span className="proc-value">{p.mem_percent}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* History Card */}
        <div className="card card-wide">
          <div className="card-header">
            <span className="card-icon">📈</span>
            <h2>History</h2>
            <div className="period-selector">
              {['1h', '6h', '24h', '7d'].map(p => (
                <button
                  key={p}
                  className={`period-btn ${historyPeriod === p ? 'active' : ''}`}
                  onClick={() => setHistoryPeriod(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div className="card-body">
            {history && history.data && history.data.length > 1 ? (
              <div className="history-charts">
                <div className="chart-container">
                  <h4>CPU Usage %</h4>
                  <div className="mini-chart">
                    {renderMiniChart(history.data.map(d => ({ time: new Date(d.timestamp).toLocaleTimeString(), value: d.cpu_usage_percent })), '#3b82f6')}
                  </div>
                </div>
                <div className="chart-container">
                  <h4>Memory Usage %</h4>
                  <div className="mini-chart">
                    {renderMiniChart(history.data.map(d => ({ time: new Date(d.timestamp).toLocaleTimeString(), value: d.mem_usage_percent })), '#22c55e')}
                  </div>
                </div>
              </div>
            ) : (
              <p className="no-data">Collecting history data... ({history?.count || 0} samples so far)</p>
            )}
          </div>
        </div>
      </div>

      {showAdmin && <AdminPanel onClose={() => setShowAdmin(false)} />}

      <footer className="footer">
        <span>Server Stats Monitor v2.0.0</span>
        <span>Signed in as {user?.username || 'user'} · Auto-refresh {autoRefresh ? 'ON' : 'OFF'}</span>
      </footer>
    </div>
  );
}

function renderMiniChart(data, color) {
  if (data.length < 2) return <div className="chart-placeholder">Need at least 2 data points</div>;

  const w = 400, h = 80;
  const maxV = Math.max(...data.map(d => d.value), 100);
  const minV = Math.min(...data.map(d => d.value), 0);
  const range = maxV - minV || 1;
  const padding = 2;
  const chartW = w - padding * 2;
  const chartH = h - padding * 2;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * chartW;
    const y = padding + chartH - ((d.value - minV) / range) * chartH;
    return `${x},${y}`;
  });

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="inline-chart">
      <path d={pathD} fill="none" stroke={color} strokeWidth="2" />
      {data.length > 0 && (
        <text x={w - 50} y={h - 5} fontSize="10" fill="#94a3b8">{data[data.length - 1].value.toFixed(1)}%</text>
      )}
    </svg>
  );
}

// ── Main App with Auth ─────────────────────────────────────────────

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const [user, setUser] = useState(getCurrentUser());
  const [view, setView] = useState('dashboard'); // 'dashboard', 'traffic', or 'threat'

  const handleLogin = useCallback(() => {
    setAuthenticated(true);
    setUser(getCurrentUser());
  }, []);

  const handleLogout = useCallback(() => {
    logout();
    setAuthenticated(false);
    setUser(null);
  }, []);

  if (!authenticated) {
    return <Login onLogin={handleLogin} />;
  }

  // Navigation bar
  const nav = (
    <nav className="app-nav">
      <button
        className={`nav-btn ${view === 'dashboard' ? 'active' : ''}`}
        onClick={() => setView('dashboard')}
      >
        🖥️ Dashboard
      </button>
      <button
        className={`nav-btn ${view === 'traffic' ? 'active' : ''}`}
        onClick={() => setView('traffic')}
      >
        🚦 Traffic
      </button>
      <button
        className={`nav-btn ${view === 'threat' ? 'active' : ''}`}
        onClick={() => setView('threat')}
      >
        🛡️ Threat Intel
      </button>
      <span className="nav-user">👤 {user?.username || 'user'}</span>
      <button onClick={handleLogout} className="nav-logout" title="Sign out">🚪</button>
    </nav>
  );

  return (
    <>
      {nav}
      {view === 'dashboard' && <Dashboard user={user} onLogout={() => {}} onShowTraffic={() => setView('traffic')} />}
      {view === 'traffic' && (
        <div className="app">
          <header className="header">
            <div className="header-left">
              <h1 className="header-title">🚦 Traffic Monitor</h1>
            </div>
            <div className="header-right">
              <button onClick={() => setView('dashboard')} className="traffic-nav-btn" title="Back to Dashboard">🖥️ Dashboard</button>
            </div>
          </header>
          <TrafficPanel />
          <footer className="footer">
            <span>Server Stats Monitor v2.0.0 · Real-time Traffic</span>
            <span>WebSocket auto-connects · Falls back to polling</span>
          </footer>
        </div>
      )}
      {view === 'threat' && (
        <div className="app">
          <header className="header">
            <div className="header-left">
              <h1 className="header-title">🛡️ Threat Intelligence</h1>
            </div>
            <div className="header-right">
              <button onClick={() => setView('dashboard')} className="traffic-nav-btn" title="Back to Dashboard">🖥️ Dashboard</button>
            </div>
          </header>
          <ThreatPanel />
          <footer className="footer">
            <span>Server Stats Monitor v2.0.0 · IP Reputation & Threat Intel</span>
            <span>Real-time IP enrichment · Multi-provider fallback</span>
          </footer>
        </div>
      )}
    </>
  );
}

export default App;