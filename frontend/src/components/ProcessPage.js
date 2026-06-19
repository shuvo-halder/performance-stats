import React, { useState, useEffect, useCallback } from 'react';
import { getMonitoredProcesses, createMonitoredProcess, deleteMonitoredProcess, checkMonitoredProcess, checkAllProcesses, getProcessEvents } from '../api';

export default function ProcessPage() {
  const [processes, setProcesses] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ process_name: '', service_name: '', auto_restart: false, max_restarts: 3 });
  const [events, setEvents] = useState(null);

  const fetch = useCallback(async () => {
    try { setProcesses((await getMonitoredProcesses()).processes || []); } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleCreate = async () => {
    try { await createMonitoredProcess(form); setShowForm(false); fetch(); } catch (e) { alert(e.message); }
  };
  const handleCheck = async (id) => { await checkMonitoredProcess(id); fetch(); };
  const handleCheckAll = async () => { await checkAllProcesses(); fetch(); };
  const handleDelete = async (id) => { await deleteMonitoredProcess(id); fetch(); };
  const showEvents = async (id, name) => {
    try { const e = await getProcessEvents(id); setEvents({ events: e.events || [], name }); } catch (e) { /* ignore */ }
  };

  return (
    <div className="grafana-dashboard">
      <div className="grafana-header">
        <div className="grafana-header-left"><h1 className="grafana-title"><span className="grafana-logo">⚙️</span> Process Monitor</h1></div>
        <div className="grafana-header-right">
          <button className="mode-btn" onClick={handleCheckAll}>Check All</button>
          <button className="mode-btn" onClick={() => setShowForm(true)}>+ Add</button>
        </div>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:500}}>
            <div className="modal-header"><h2>Add Process</h2><button className="modal-close" onClick={() => setShowForm(false)}>×</button></div>
            <div className="modal-body">
              <div className="form-group"><label>PROCESS NAME</label><input value={form.process_name} onChange={e => setForm({...form,process_name:e.target.value})} placeholder="nginx" /></div>
              <div className="form-group"><label>SERVICE NAME (systemd)</label><input value={form.service_name} onChange={e => setForm({...form,service_name:e.target.value})} placeholder="nginx" /></div>
              <div className="form-group"><label>MAX RESTARTS</label><input type="number" value={form.max_restarts} onChange={e => setForm({...form,max_restarts:parseInt(e.target.value)||3})} /></div>
              <div className="form-group">
                <label><input type="checkbox" checked={form.auto_restart} onChange={e => setForm({...form,auto_restart:e.target.checked})} style={{accentColor:'#3b82f6',marginRight:8}} /> Auto-Restart</label>
              </div>
              <button className="login-btn" onClick={handleCreate}>Add</button>
            </div>
          </div>
        </div>
      )}

      <div className="grafana-charts-grid" style={{gridTemplateColumns:'1fr'}}>
        <div className="grafana-panel">
          <div className="panel-header"><span className="panel-title">Processes</span></div>
          <div className="panel-body">
            {processes.length === 0 ? <div className="chart-placeholder">No processes monitored</div> : (
              <div className="grafana-table">
                <div className="grafana-table-header" style={{gridTemplateColumns:'1.5fr 1fr 70px 70px 80px 60px 90px 100px'}}>
                  <span>Process</span><span>Service</span><span>CPU%</span><span>MEM%</span><span>Uptime</span><span>Status</span><span>Restarts</span><span>Actions</span>
                </div>
                {processes.map(p => (
                  <div key={p.id} className="grafana-table-row" style={{gridTemplateColumns:'1.5fr 1fr 70px 70px 80px 60px 90px 100px'}}>
                    <span style={{fontWeight:600}}>{p.process_name}</span>
                    <span style={{fontSize:11}}>{p.service_name || '—'}</span>
                    <span>{p.cpu_percent}%</span>
                    <span>{p.mem_percent}%</span>
                    <span style={{fontSize:11}}>{p.uptime_seconds ? `${Math.floor(p.uptime_seconds/3600)}h` : '—'}</span>
                    <span style={{color:p.is_running?'#22c55e':'#ef4444',fontWeight:600}}>{p.is_running ? 'ON' : 'OFF'}</span>
                    <span style={{fontSize:11}}>{p.restart_count}/{p.max_restarts}</span>
                    <span style={{display:'flex',gap:4}}>
                      <button className="mode-btn" onClick={() => handleCheck(p.id)}>Check</button>
                      <button className="mode-btn" onClick={() => showEvents(p.id, p.process_name)}>Events</button>
                      <button className="mode-btn" style={{color:'#ef4444'}} onClick={() => handleDelete(p.id)}>Del</button>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {events && (
        <div className="modal-overlay" onClick={() => setEvents(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:500}}>
            <div className="modal-header"><h2>Events: {events.name}</h2><button className="modal-close" onClick={() => setEvents(null)}>×</button></div>
            <div className="modal-body">
              {events.events.length === 0 ? <div className="chart-placeholder">No events</div> : (
                <div className="grafana-table">
                  {events.events.map((e,i) => (
                    <div key={i} className="grafana-table-row" style={{gridTemplateColumns:'80px 1fr'}}>
                      <span style={{color:e.event_type==='RESTARTED'?'#f59e0b':e.event_type==='STOPPED'?'#ef4444':'#22c55e',fontWeight:600,fontSize:11}}>{e.event_type}</span>
                      <span style={{fontSize:11}}>{e.message} — {e.created_at ? new Date(e.created_at).toLocaleString() : ''}</span>
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