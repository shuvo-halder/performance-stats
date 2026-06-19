import React, { useState, useEffect, useCallback } from 'react';
import { scanSSL, getSSLCertificates, getSSLCertificate, deleteSSLCertificate } from '../api';

const expiryColor = (d) => { if (d <= 3) return '#ef4444'; if (d <= 7) return '#f59e0b'; if (d <= 15) return '#f97316'; if (d <= 30) return '#eab308'; return '#22c55e'; };

export default function SSLPage() {
  const [certs, setCerts] = useState([]);
  const [hostname, setHostname] = useState('');
  const [scanning, setScanning] = useState(false);
  const [detail, setDetail] = useState(null);

  const fetch = useCallback(async () => { try { setCerts((await getSSLCertificates()).certificates || []); } catch (e) { /* ignore */ } }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleScan = async () => {
    if (!hostname) return;
    setScanning(true);
    try {
      await scanSSL(hostname);
      setHostname('');
      fetch();
    } catch (e) { alert(e.message); }
    setScanning(false);
  };

  const handleDelete = async (id, hostname) => {
    if (!window.confirm(`Delete certificate for "${hostname}"?`)) return;
    try {
      await deleteSSLCertificate(id);
      fetch();
    } catch (e) { alert(e.message); }
  };

  const showDetail = async (id) => {
    try { setDetail(await getSSLCertificate(id)); } catch (e) { /* ignore */ }
  };

  return (
    <div className="grafana-dashboard">
      <div className="grafana-header">
        <div className="grafana-header-left"><h1 className="grafana-title"><span className="grafana-logo">🔒</span> SSL Certificate Monitor</h1></div>
        <div className="grafana-header-right">
          <input value={hostname} onChange={e => setHostname(e.target.value)} placeholder="example.com" style={{padding:'6px 12px',background:'#0f172a',border:'1px solid #334155',borderRadius:4,color:'#e2e8f0',fontSize:13,width:200}} />
          <button className="mode-btn" onClick={handleScan} disabled={scanning}>{scanning ? 'Scanning...' : 'Scan'}</button>
        </div>
      </div>

      <div className="grafana-charts-grid" style={{gridTemplateColumns:'1fr'}}>
        <div className="grafana-panel">
          <div className="panel-header"><span className="panel-title">Certificates</span></div>
          <div className="panel-body">
            {certs.length === 0 ? <div className="chart-placeholder">No certificates scanned</div> : (
              <div className="grafana-table">
                <div className="grafana-table-header" style={{gridTemplateColumns:'1.5fr 1fr 1fr 100px 100px 80px'}}>
                  <span>Hostname</span><span>Issuer</span><span>Expires</span><span>Days Left</span><span>Status</span><span>Actions</span>
                </div>
                {certs.map(c => (
                  <div key={c.id} className="grafana-table-row" style={{gridTemplateColumns:'1.5fr 1fr 1fr 100px 100px 80px'}}>
                    <span className="grafana-ip">{c.hostname}</span>
                    <span style={{fontSize:11}}>{c.issuer ? c.issuer.substring(0,40)+'...' : '—'}</span>
                    <span style={{fontSize:11}}>{c.valid_to ? new Date(c.valid_to).toLocaleDateString() : '—'}</span>
                    <span style={{color:expiryColor(c.days_remaining||999),fontWeight:700}}>{c.days_remaining !== null ? `${c.days_remaining}d` : '—'}</span>
                    <span style={{color:c.status==='VALID'?'#22c55e':c.status==='EXPIRING_SOON'?'#f59e0b':'#ef4444',fontWeight:600}}>{c.status}</span>
                    <span style={{display:'flex',gap:4}}>
                      <button className="mode-btn" onClick={() => showDetail(c.id)}>View</button>
                      <button className="mode-btn" style={{color:'#ef4444'}} onClick={() => handleDelete(c.id, c.hostname)}>Del</button>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth:600}}>
            <div className="modal-header"><h2>SSL: {detail.hostname}</h2><button className="modal-close" onClick={() => setDetail(null)}>×</button></div>
            <div className="modal-body">
              <div className="ip-details-grid">
                <div className="detail-section"><h3>Certificate Info</h3>
                  <div className="detail-row"><span className="detail-label">Issuer</span><span className="detail-value">{detail.issuer}</span></div>
                  <div className="detail-row"><span className="detail-label">Subject</span><span className="detail-value">{detail.subject}</span></div>
                  <div className="detail-row"><span className="detail-label">Algorithm</span><span className="detail-value">{detail.algorithm}</span></div>
                </div>
                <div className="detail-section"><h3>Validity</h3>
                  <div className="detail-row"><span className="detail-label">Valid From</span><span className="detail-value">{detail.valid_from ? new Date(detail.valid_from).toLocaleDateString() : '—'}</span></div>
                  <div className="detail-row"><span className="detail-label">Valid To</span><span className="detail-value">{detail.valid_to ? new Date(detail.valid_to).toLocaleDateString() : '—'}</span></div>
                  <div className="detail-row"><span className="detail-label">Days Left</span><span className="detail-value" style={{color:expiryColor(detail.days_remaining||999)}}>{detail.days_remaining !== null ? `${detail.days_remaining}d` : '—'}</span></div>
                </div>
              </div>
              {detail.sans?.length > 0 && (
                <div style={{marginTop:8}} className="detail-section">
                  <h3>SAN Domains ({detail.sans.length})</h3>
                  <div style={{display:'flex',flexWrap:'wrap',gap:4}}>
                    {detail.sans.map((s,i) => <span key={i} className="threat-flag-sm">{s}</span>)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}