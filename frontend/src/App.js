import React, { useState, useEffect, useCallback } from 'react';
import Login from './components/Login';
import AdminPanel from './components/AdminPanel';
import TrafficPanel from './components/TrafficPanel';
import ThreatPanel from './components/ThreatPanel';
import GrafanaDashboard from './components/GrafanaDashboard';
import AlertCenter from './components/AlertCenter';
import ServersPage from './components/ServersPage';
import UptimePage from './components/UptimePage';
import SSLPage from './components/SSLPage';
import ProcessPage from './components/ProcessPage';
import { getCurrentUser, isAuthenticated, logout } from './api';
import './styles/dashboard.css';

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const [user, setUser] = useState(getCurrentUser());
  const [view, setView] = useState('dashboard');

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

  const nav = (
    <nav className="app-nav">
      <button className={`nav-btn ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}>📊 Monitor</button>
      <button className={`nav-btn ${view === 'alerts' ? 'active' : ''}`} onClick={() => setView('alerts')}>🔔 Alerts</button>
      <button className={`nav-btn ${view === 'servers' ? 'active' : ''}`} onClick={() => setView('servers')}>🖥️ Servers</button>
      <button className={`nav-btn ${view === 'uptime' ? 'active' : ''}`} onClick={() => setView('uptime')}>⏱️ Uptime</button>
      <button className={`nav-btn ${view === 'ssl' ? 'active' : ''}`} onClick={() => setView('ssl')}>🔒 SSL</button>
      <button className={`nav-btn ${view === 'processes' ? 'active' : ''}`} onClick={() => setView('processes')}>⚙️ Processes</button>
      <button className={`nav-btn ${view === 'traffic' ? 'active' : ''}`} onClick={() => setView('traffic')}>🚦 Traffic</button>
      <button className={`nav-btn ${view === 'threat' ? 'active' : ''}`} onClick={() => setView('threat')}>🛡️ Threat</button>
      <span className="nav-user">👤 {user?.username || 'user'}</span>
      <button onClick={handleLogout} className="nav-logout" title="Sign out">🚪</button>
    </nav>
  );

  return (
    <>
      {nav}
      {view === 'dashboard' && <GrafanaDashboard />}
      {view === 'alerts' && <AlertCenter />}
      {view === 'servers' && <ServersPage />}
      {view === 'uptime' && <UptimePage />}
      {view === 'ssl' && <SSLPage />}
      {view === 'processes' && <ProcessPage />}
      {view === 'traffic' && <TrafficPanel />}
      {view === 'threat' && <ThreatPanel />}
    </>
  );
}

export default App;