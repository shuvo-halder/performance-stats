import React, { useState, useEffect, useCallback } from 'react';
import Login from './components/Login';
import AdminPanel from './components/AdminPanel';
import TrafficPanel from './components/TrafficPanel';
import ThreatPanel from './components/ThreatPanel';
import GrafanaDashboard from './components/GrafanaDashboard';
import { getCurrentUser, isAuthenticated, logout } from './api';
import './styles/dashboard.css';

function Dashboard({ user, onLogout, onShowTraffic }) {
  const [showAdmin, setShowAdmin] = useState(false);
  return (
    <>
      <GrafanaDashboard />
      {showAdmin && <AdminPanel onClose={() => setShowAdmin(false)} />}
    </>
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