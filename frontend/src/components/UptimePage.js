import React, { useState, useEffect, useCallback } from 'react';
import { getUptimeMonitors, createUptimeMonitor, deleteUptimeMonitor, checkUptimeNow, getUptimeHistory, getUptimeIncidents } from '../api';

export default function UptimePage() {
  const [monitors, setMonitors] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', monitor_type: 'https', target: '', check_interval: 60, timeout: 10, expected_status_code: 200 });
  const [details, setDetails] = useState(null);

  const fetch = useCallback(async () => {
    try { setMonitors((await getUptimeMonitors()).monitors || []); } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleCreate = async () => {
    try { await createUptimeMonitor(form); setShowForm(false); fetch(); } catch (e) { alert(e.message); }
  };
  const handleCheck = async (id) => { await checkUptimeNow(id); fetch(); };
  const handleDelete = async (id) => { await deleteUptimeMonitor(id); fetch(); };
  const showDetails = async (id) => {
    try {
      const h = await getUptimeHistory(id);
      const i = await getUptimeIncidents(id);
      setDetails({ history: h.results || [], incidents: i.incidents || [] });
    } catch (e) { /* ignore */ }
  };

  const statusColor = { UP: '#22c55e', DOWN: '#ef4444', UNKNOWN: '#64748b' };

  return (
    <div className="grafana-dashboard">
      <div className="grafana-header">
        <div className="grafana-header-left"><h1 className="grafana-title"><span className="grafana-logo">⏱️</span> Uptime Monitor</h1></div>
        <div className="grafana-header-right"><button className="mode-btn" onClick={() => setShowForm(true)}>+ Monitor</button></div>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:500}}>
            <div className="modal-header"><h2>Create Monitor</h2><button className="modal-close" onClick={() => setShowForm(false)}>×</button></div>
            <div className="modal-body">
              {['name','target','check_interval','timeout','expected_status_code'].map(f => (
                <div className="form-group" key={f}>
                  <label>{f.toUpperCase()}</label>
                  <input value={form[f]} onChange={e => setForm({...form,[f]:e.target.value})} placeholder={f} />
                </div>
              ))}
              <div className="form-group">
                <label>TYPE</label>
                <select value={form.monitor_type} onChange={e => setForm({...form,monitor_type:e.target.value})} style={{width:'100%',padding:10,background:'#0f172a',border:'1px solid #334155',borderRadius:6,color:'#e2e8f0'}}>
                  <option value="https">HTTPS</option><option value="http">HTTP</option><option value="tcp">TCP</option>
                </select>
              </div>
              <button className="login-btn" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      <div className="grafana-charts-grid" style={{gridTemplateColumns:'1fr'}}>
        <div className="grafana-panel">
          <div className="panel-header"><span className="panel-title">Monitors</span></div>
          <div className="panel-body">
            {monitors.length === 0 ? <div className="chart-placeholder">No monitors configured</div> : (
              <div className="grafana-table">
                <div className="grafana-table-header" style={{gridTemplateColumns:'1.5fr 1fr 70px 80px 80px 100px 150px'}}>
                  <span>Name</span><span>Target</span><span>Type</span><span>Uptime</span><span>Status</span><span>Response</span><span>Actions</span>
                </div>
                {monitors.map(m => (
                  <div key={m.id} className="grafana-table-row" style={{gridTemplateColumns:'1.5fr 1fr 70px 80px 80px 100px 150px'}}>
                    <span style={{fontWeight:600}}>{m.name}</span>
                    <span className="grafana-ip">{m.target}</span>
                    <span style={{fontSize:11}}>{m.monitor_type}</span>
                    <span style={{color:m.uptime_percent>99?'#22c55e':'#f59e0b',fontWeight:600}}>{m.uptime_percent}%</span>
                    <span style={{color:statusColor[m.last_status]||'#64748b',fontWeight:600}}>{m.last_status||'—'}</span>
                    <span style={{fontSize:11}}>{m.response_time_ms ? `${m.response_time_ms.toFixed(0)}ms` : '—'}</span>
                    <span style={{display:'flex',gap:4}}>
                      <button className="mode-btn" onClick={() => handleCheck(m.id)}>Check</button>
                      <button className="mode-btn" onClick={() => showDetails(m.id)}>Logs</button>
                      <button className="mode-btn" style={{color:'#ef4444'}} onClick={() => handleDelete(m.id)}>Del</button>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {details && (
        <div className="modal-overlay" onClick={() => setDetails(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:600}}>
            <div className="modal-header"><h2>Check History</h2><button className="modal-close" onClick={() => setDetails(null)}>×</button></div>
            <div className="modal-body">
              <h4 style={{color:'#94a3b8',marginBottom:8}}>Recent Results</h4>
              <div className="grafana-table">
                {details.history.slice(0,20).map((h,i) => (
                  <div key={i} className="grafana-table-row" style={{gridTemplateColumns:'1fr 60px 80px'}}>
                    <span style={{fontSize:10}}>{h.timestamp ? new Date(h.timestamp).toLocaleString() : '—'}</span>
                    <span style={{color:h.status==='UP'?'#22c55e':'#ef4444',fontWeight:600}}>{h.status}</span>
                    <span>{h.response_time_ms ? `${h.response_time_ms.toFixed(0)}ms` : '—'}</span>
                  </div>
                ))}
              </div>
              {details.incidents.filter(i => i.is_active).length > 0 && (
                <div style={{marginTop:12,padding:10,background:'#7f1d1d40',borderRadius:6,border:'1px solid #dc2626'}}>
                  ⚠ Active incident since {new Date(details.incidents.find(i=>i.is_active).started_at).toLocaleString()}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}