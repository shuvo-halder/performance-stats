import React, { useState, useEffect, useCallback } from 'react';
import { getServers, getServerSummary, registerServer, deleteServer } from '../api';

export default function ServersPage() {
  const [servers, setServers] = useState([]);
  const [summary, setSummary] = useState({ total: 0, online: 0, offline: 0, warning: 0, critical: 0 });
  const [showRegister, setShowRegister] = useState(false);
  const [form, setForm] = useState({ hostname: '', public_ip: '', os: '', kernel: '' });
  const [newToken, setNewToken] = useState('');

  const fetch = useCallback(async () => {
    try {
      setServers((await getServers()).servers || []);
      setSummary(await getServerSummary());
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleRegister = async () => {
    try {
      const data = await registerServer(form);
      setNewToken(data.token);
      setShowRegister(false);
      fetch();
    } catch (e) { alert(e.message); }
  };

  const handleDeleteServer = async (id, hostname) => {
    if (!window.confirm(`Delete server "${hostname}"?`)) return;
    try {
      await deleteServer(id);
      fetch();
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="grafana-dashboard">
      <div className="grafana-header">
        <div className="grafana-header-left"><h1 className="grafana-title"><span className="grafana-logo">🖥️</span> Server Infrastructure</h1></div>
        <div className="grafana-header-right">
          {!newToken && <button className="mode-btn" onClick={() => setShowRegister(true)}>+ Register</button>}
        </div>
      </div>

      <div className="threat-summary-grid" style={{gridTemplateColumns:'repeat(5,1fr)'}}>
        <div className="threat-stat-card default-bg"><div className="threat-stat-value">{summary.total}</div><div className="threat-stat-label">Total</div></div>
        <div className="threat-stat-card" style={{background:'#22c55e20',borderColor:'#22c55e'}}><div className="threat-stat-value">{summary.online}</div><div className="threat-stat-label">Online</div></div>
        <div className="threat-stat-card" style={{background:'#ef444420',borderColor:'#ef4444'}}><div className="threat-stat-value">{summary.offline}</div><div className="threat-stat-label">Offline</div></div>
        <div className="threat-stat-card suspicious-bg"><div className="threat-stat-value">{summary.warning}</div><div className="threat-stat-label">Warning</div></div>
        <div className="threat-stat-card malicious-bg"><div className="threat-stat-value">{summary.critical}</div><div className="threat-stat-label">Critical</div></div>
      </div>

      {newToken && (
        <div className="grafana-panel" style={{marginBottom:8,borderColor:'#22c55e'}}>
          <div className="panel-body">
            <strong style={{color:'#22c55e'}}>✅ Server Registered!</strong><br/>
            <span>Agent Token: <code style={{color:'#fbbf24'}}>{newToken}</code></span><br/>
            <span style={{fontSize:12,color:'#64748b'}}>Install agent: curl -sSL https://your-server.com/install.sh | bash -s -- --server {window.location.origin} --token {newToken.substring(0,8)}...</span>
          </div>
        </div>
      )}

      {showRegister && (
        <div className="modal-overlay" onClick={() => setShowRegister(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:500}}>
            <div className="modal-header"><h2>Register Server</h2><button className="modal-close" onClick={() => setShowRegister(false)}>×</button></div>
            <div className="modal-body">
              {['hostname','public_ip','os','kernel'].map(f => (
                <div className="form-group" key={f}>
                  <label>{f.toUpperCase()}</label>
                  <input value={form[f]} onChange={e => setForm({...form,[f]:e.target.value})} placeholder={f} />
                </div>
              ))}
              <button className="login-btn" onClick={handleRegister}>Register</button>
            </div>
          </div>
        </div>
      )}

      <div className="grafana-charts-grid" style={{gridTemplateColumns:'1fr'}}>
        <div className="grafana-panel">
          <div className="panel-header"><span className="panel-title">Servers</span></div>
          <div className="panel-body">
            {servers.length === 0 ? <div className="chart-placeholder">No servers registered</div> : (
              <div className="grafana-table">
                <div className="grafana-table-header" style={{gridTemplateColumns:'1.5fr 1fr 1fr 1fr 80px 100px 60px'}}>
                  <span>Hostname</span><span>IP</span><span>OS</span><span>Agent</span><span>Status</span><span>Last Seen</span><span>Action</span>
                </div>
                {servers.map(s => (
                  <div key={s.id} className="grafana-table-row" style={{gridTemplateColumns:'1.5fr 1fr 1fr 1fr 80px 100px 60px'}}>
                    <span className="grafana-ip">{s.hostname}</span><span>{s.public_ip || '—'}</span>
                    <span style={{fontSize:11}}>{s.os || '—'}</span><span style={{fontSize:11}}>{s.agent_version || '—'}</span>
                    <span style={{color:s.status==='ONLINE'?'#22c55e':s.status==='WARNING'?'#f59e0b':'#ef4444',fontWeight:600}}>{s.status}</span>
                    <span style={{fontSize:10}}>{s.last_seen ? new Date(s.last_seen).toLocaleString() : '—'}</span>
                    <span><button className="mode-btn" style={{color:'#ef4444',fontSize:11,padding:'2px 6px'}} onClick={() => handleDeleteServer(s.id, s.hostname)}>🗑️</button></span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}