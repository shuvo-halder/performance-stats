import React, { useState, useEffect, useCallback } from 'react';
import { getUptimeMonitors, createUptimeMonitor, updateUptimeMonitor, deleteUptimeMonitor, checkUptimeNow, checkAllUptime, getUptimeHistory, getUptimeIncidents } from '../api';

export default function UptimePage() {
  const [monitors, setMonitors] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', monitor_type: 'https', target: '', check_interval: 60, timeout: 10, retry_count: 2, expected_status_code: 200, expected_content: '' });
  const [editForm, setEditForm] = useState(null);
  const [details, setDetails] = useState(null);
  const [checking, setChecking] = useState(null);
  const [checkAllLoading, setCheckAllLoading] = useState(false);

  const fetch = useCallback(async () => {
    try { setMonitors((await getUptimeMonitors()).monitors || []); } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleCreate = async () => {
    try {
      const payload = { ...form, check_interval: Number(form.check_interval), timeout: Number(form.timeout), retry_count: Number(form.retry_count), expected_status_code: Number(form.expected_status_code) };
      await createUptimeMonitor(payload); setShowForm(false); fetch();
    } catch (e) { alert(e.message); }
  };

  const handleCheck = async (id) => {
    setChecking(id);
    try { await checkUptimeNow(id); fetch(); } catch (e) { alert(e.message); }
    finally { setChecking(null); }
  };

  const handleCheckAll = async () => {
    setCheckAllLoading(true);
    try { await checkAllUptime(); fetch(); } catch (e) { alert(e.message); }
    finally { setCheckAllLoading(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this monitor?')) return;
    try { await deleteUptimeMonitor(id); fetch(); } catch (e) { alert(e.message); }
  };

  const handleToggleEnabled = async (m) => {
    try { await updateUptimeMonitor(m.id, { enabled: !m.enabled }); fetch(); } catch (e) { alert(e.message); }
  };

  const handleEdit = async () => {
    try {
      const payload = { ...editForm, check_interval: Number(editForm.check_interval), timeout: Number(editForm.timeout), retry_count: Number(editForm.retry_count), expected_status_code: Number(editForm.expected_status_code) };
      await updateUptimeMonitor(payload.id, payload); setEditForm(null); fetch();
    } catch (e) { alert(e.message); }
  };

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
        <div className="grafana-header-right">
          <button className="mode-btn" onClick={handleCheckAll} disabled={checkAllLoading} style={{marginRight:8}}>
            {checkAllLoading ? 'Checking...' : 'Check All'}
          </button>
          <button className="mode-btn" onClick={() => setShowForm(true)}>+ Monitor</button>
        </div>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:500}}>
            <div className="modal-header"><h2>Create Monitor</h2><button className="modal-close" onClick={() => setShowForm(false)}>×</button></div>
            <div className="modal-body">
              {['name','target','check_interval','timeout','retry_count','expected_status_code'].map(f => (
                <div className="form-group" key={f}>
                  <label>{f.toUpperCase()}</label>
                  <input value={form[f]} onChange={e => setForm({...form,[f]:e.target.value})} placeholder={f} />
                </div>
              ))}
              <div className="form-group">
                <label>EXPECTED CONTENT (optional)</label>
                <input value={form.expected_content} onChange={e => setForm({...form,expected_content:e.target.value})} placeholder="e.g. Welcome" />
              </div>
              <div className="form-group">
                <label>TYPE</label>
                <select value={form.monitor_type} onChange={e => setForm({...form,monitor_type:e.target.value})} style={{width:'100%',padding:10,background:'#0f172a',border:'1px solid #334155',borderRadius:6,color:'#e2e8f0'}}>
                  <option value="https">HTTPS</option><option value="http">HTTP</option><option value="tcp">TCP</option><option value="icmp">ICMP (Ping)</option>
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
                <div className="grafana-table-header" style={{gridTemplateColumns:'40px 1.5fr 1fr 60px 60px 80px 70px 100px 150px'}}>
                  <span></span><span>Name</span><span>Target</span><span>Type</span><span>Uptime</span><span>Status</span><span>Response</span><span>Interval</span><span>Actions</span>
                </div>
                {monitors.map(m => (
                  <div key={m.id} className="grafana-table-row" style={{gridTemplateColumns:'40px 1.5fr 1fr 60px 60px 80px 70px 100px 150px', opacity: m.enabled===false ? 0.5 : 1}}>
                    <span>
                      <input type="checkbox" checked={m.enabled!==false} onChange={() => handleToggleEnabled(m)} title="Enable/Disable" style={{cursor:'pointer'}} />
                    </span>
                    <span style={{fontWeight:600}}>{m.name}</span>
                    <span className="grafana-ip">{m.target}</span>
                    <span style={{fontSize:11}}>{m.monitor_type}</span>
                    <span style={{color:m.uptime_percent>99?'#22c55e':'#f59e0b',fontWeight:600}}>{m.uptime_percent}%</span>
                    <span style={{color:statusColor[m.last_status]||'#64748b',fontWeight:600}}>{m.last_status||'—'}</span>
                    <span style={{fontSize:11}}>{m.response_time_ms ? `${m.response_time_ms.toFixed(0)}ms` : '—'}</span>
                    <span style={{fontSize:10,color:'#94a3b8'}}>{m.check_interval}s</span>
                    <span style={{display:'flex',gap:4,flexWrap:'wrap'}}>
                      <button className="mode-btn" style={{fontSize:10,padding:'4px 8px'}} onClick={() => handleCheck(m.id)} disabled={checking === m.id}>
                        {checking === m.id ? '...' : 'Check'}
                      </button>
                      <button className="mode-btn" style={{fontSize:10,padding:'4px 8px'}} onClick={() => showDetails(m.id)}>Logs</button>
                      <button className="mode-btn" style={{fontSize:10,padding:'4px 8px'}} onClick={() => setEditForm({id:m.id, name:m.name, monitor_type:m.monitor_type, target:m.target, check_interval:m.check_interval, timeout:m.timeout, retry_count:m.retry_count||2, expected_status_code:m.expected_status_code, expected_content:m.expected_content||'', enabled:m.enabled})}>Edit</button>
                      <button className="mode-btn" style={{fontSize:10,padding:'4px 8px',color:'#ef4444'}} onClick={() => handleDelete(m.id)}>Del</button>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {editForm && (
        <div className="modal-overlay" onClick={() => setEditForm(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:500}}>
            <div className="modal-header"><h2>Edit Monitor</h2><button className="modal-close" onClick={() => setEditForm(null)}>×</button></div>
            <div className="modal-body">
              {['name','target','check_interval','timeout','retry_count','expected_status_code'].map(f => (
                <div className="form-group" key={f}>
                  <label>{f.toUpperCase()}</label>
                  <input value={editForm[f]} onChange={e => setEditForm({...editForm,[f]:e.target.value})} placeholder={f} />
                </div>
              ))}
              <div className="form-group">
                <label>EXPECTED CONTENT (optional)</label>
                <input value={editForm.expected_content} onChange={e => setEditForm({...editForm,expected_content:e.target.value})} placeholder="e.g. Welcome" />
              </div>
              <div className="form-group">
                <label>TYPE</label>
                <select value={editForm.monitor_type} onChange={e => setEditForm({...editForm,monitor_type:e.target.value})} style={{width:'100%',padding:10,background:'#0f172a',border:'1px solid #334155',borderRadius:6,color:'#e2e8f0'}}>
                  <option value="https">HTTPS</option><option value="http">HTTP</option><option value="tcp">TCP</option><option value="icmp">ICMP (Ping)</option>
                </select>
              </div>
              <button className="login-btn" onClick={handleEdit}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {details && (
        <div className="modal-overlay" onClick={() => setDetails(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:700}}>
            <div className="modal-header"><h2>Check History</h2><button className="modal-close" onClick={() => setDetails(null)}>×</button></div>
            <div className="modal-body">
              <h4 style={{color:'#94a3b8',marginBottom:8}}>Recent Results</h4>
              <div className="grafana-table">
                <div className="grafana-table-header" style={{gridTemplateColumns:'1fr 60px 80px'}}>
                  <span>Timestamp</span><span>Status</span><span>Response</span>
                </div>
                {details.history.slice(0,30).map((h,i) => (
                  <div key={i} className="grafana-table-row" style={{gridTemplateColumns:'1fr 60px 80px'}}>
                    <span style={{fontSize:10}}>{h.timestamp ? new Date(h.timestamp).toLocaleString() : '—'}</span>
                    <span style={{color:h.status==='UP'?'#22c55e':'#ef4444',fontWeight:600}}>{h.status}</span>
                    <span>{h.response_time_ms ? `${h.response_time_ms.toFixed(0)}ms` : '—'}</span>
                  </div>
                ))}
              </div>
              {details.incidents.length > 0 && (
                <div style={{marginTop:16}}>
                  <h4 style={{color:'#94a3b8',marginBottom:8}}>Incidents</h4>
                  {details.incidents.map((inc,i) => (
                    <div key={i} style={{padding:'6px 10px',marginBottom:4,background:inc.is_active?'#7f1d1d40':'#1e293b',borderRadius:6,border:inc.is_active?'1px solid #dc2626':'1px solid #334155',fontSize:12}}>
                      <span style={{color:inc.is_active?'#ef4444':'#94a3b8',fontWeight:600}}>
                        {inc.is_active ? '⚠ Active' : '✓ Resolved'}
                      </span>
                      {' '}{new Date(inc.started_at).toLocaleString()}
                      {inc.ended_at && ` → ${new Date(inc.ended_at).toLocaleString()}`}
                      {inc.duration && ` (${Math.floor(inc.duration/60)}m ${inc.duration%60}s)`}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}