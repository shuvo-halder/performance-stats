import React, { useState, useEffect, useCallback } from 'react';
import { getActiveAlerts, getAlertHistory, getAlertRules, createAlertRule, deleteAlertRule, acknowledgeAlert, resolveAlert, getAlertChannels, createAlertChannel, deleteAlertChannel, testAlertChannel } from '../api';

const severityColor = { INFO: '#3b82f6', WARNING: '#f59e0b', CRITICAL: '#ef4444' };

export default function AlertCenter() {
  const [alerts, setAlerts] = useState([]);
  const [rules, setRules] = useState([]);
  const [tab, setTab] = useState('active');
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [channels, setChannels] = useState([]);

  const fetch = useCallback(async () => {
    try {
      if (tab === 'active') setAlerts((await getActiveAlerts()).alerts || []);
      else setAlerts((await getAlertHistory(200, tab === 'all' ? null : tab)).alerts || []);
      setRules((await getAlertRules()).rules || []);
      setChannels((await getAlertChannels()).channels || []);
    } catch (e) { /* ignore */ }
  }, [tab]);

  useEffect(() => { fetch(); }, [fetch]);

  const handleAck = async (id) => { await acknowledgeAlert(id, 'admin'); fetch(); };
  const handleResolve = async (id) => { await resolveAlert(id, 'admin'); fetch(); };

  return (
    <div className="grafana-dashboard">
      <div className="grafana-header">
        <div className="grafana-header-left"><h1 className="grafana-title"><span className="grafana-logo">🔔</span> Alert Center</h1></div>
        <div className="grafana-header-right">
          <button className="mode-btn" onClick={() => setShowRuleModal(true)}>+ Rule</button>
          <button className="mode-btn" onClick={() => setShowChannelModal(true)}>+ Channel</button>
        </div>
      </div>

      <div className="threat-summary-grid" style={{gridTemplateColumns:'repeat(4,1fr)'}}>
        <div className="threat-stat-card info-bg"><div className="threat-stat-value">{rules.length}</div><div className="threat-stat-label">Rules</div></div>
        <div className="threat-stat-card malicious-bg"><div className="threat-stat-value">{alerts.filter(a=>a.severity==='CRITICAL').length}</div><div className="threat-stat-label">Critical</div></div>
        <div className="threat-stat-card suspicious-bg"><div className="threat-stat-value">{alerts.filter(a=>a.severity==='WARNING').length}</div><div className="threat-stat-label">Warnings</div></div>
        <div className="threat-stat-card default-bg"><div className="threat-stat-value">{channels.length}</div><div className="threat-stat-label">Channels</div></div>
      </div>

      <div className="grafana-charts-grid" style={{gridTemplateColumns:'1fr'}}>
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-title">Alerts</span>
            <div className="period-selector">
              {['active', 'all', 'RESOLVED', 'ACKNOWLEDGED'].map(t => (
                <button key={t} className={`period-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t.toUpperCase()}</button>
              ))}
            </div>
          </div>
          <div className="panel-body">
            {alerts.length === 0 ? <div className="chart-placeholder">No alerts</div> : (
              <div className="grafana-table">
                <div className="grafana-table-header" style={{gridTemplateColumns:'2fr 1fr 1fr 1fr 1.5fr'}}>
                  <span>Message</span><span>Severity</span><span>Status</span><span>Source</span><span>Actions</span>
                </div>
                {alerts.map(a => (
                  <div key={a.id} className="grafana-table-row" style={{gridTemplateColumns:'2fr 1fr 1fr 1fr 1.5fr'}}>
                    <span style={{fontSize:12}}>{a.message}</span>
                    <span style={{color:severityColor[a.severity],fontWeight:600}}>{a.severity}</span>
                    <span>{a.status}</span>
                    <span>{a.source}</span>
                    <span style={{display:'flex',gap:4}}>
                      {a.status === 'ACTIVE' && <><button className="mode-btn" onClick={() => handleAck(a.id)}>Ack</button><button className="mode-btn" onClick={() => handleResolve(a.id)}>Resolve</button></>}
                    </span>
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