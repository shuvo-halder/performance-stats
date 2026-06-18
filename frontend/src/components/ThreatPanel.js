import React, { useState, useEffect, useCallback } from 'react';
import { getIPReputationStats, getTopMaliciousIPs, getIPReputation, forceCheckIP } from '../api';

function IPDetailsModal({ ip, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        const result = await getIPReputation(ip);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [ip]);

  const handleForceCheck = async () => {
    try {
      setLoading(true);
      const result = await forceCheckIP(ip);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (score) => {
    if (score >= 70) return <span className="status-badge malicious">MALICIOUS</span>;
    if (score >= 30) return <span className="status-badge suspicious">SUSPICIOUS</span>;
    return <span className="status-badge safe">SAFE</span>;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content ip-details-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🔍 IP Details: {ip}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {loading && <div className="loading-inline"><div className="spinner-sm"></div> Checking IP reputation...</div>}
          {error && <div className="error-message">⚠️ {error}</div>}
          {data && !loading && (
            <div className="ip-details-grid">
              <div className="detail-section">
                <h3>Threat Assessment</h3>
                <div className="detail-row">
                  <span className="detail-label">Status:</span>
                  <span className="detail-value">{getStatusBadge(data.abuse_score)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Abuse Score:</span>
                  <span className="detail-value">
                    <div className="score-bar-container">
                      <div className="score-bar" style={{
                        width: `${data.abuse_score}%`,
                        backgroundColor: data.abuse_score >= 70 ? '#ef4444' : data.abuse_score >= 30 ? '#f59e0b' : '#22c55e'
                      }}></div>
                      <span className="score-text">{data.abuse_score}/100</span>
                    </div>
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Malicious:</span>
                  <span className="detail-value">{data.is_malicious ? '✅ Yes' : '❌ No'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Threat Flags:</span>
                  <span className="detail-value">
                    {data.threat_flags && data.threat_flags.length > 0
                      ? data.threat_flags.map((f, i) => <span key={i} className="threat-flag">{f}</span>)
                      : <span className="text-muted">None</span>}
                  </span>
                </div>
              </div>

              <div className="detail-section">
                <h3>Network Info</h3>
                <div className="detail-row">
                  <span className="detail-label">Country:</span>
                  <span className="detail-value">{data.country || 'Unknown'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">ISP:</span>
                  <span className="detail-value">{data.isp || 'Unknown'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Usage Type:</span>
                  <span className="detail-value">{data.usage_type || 'Unknown'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Domain (rDNS):</span>
                  <span className="detail-value">{data.domain || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">ASN:</span>
                  <span className="detail-value">{data.asn ? `${data.asn} (${data.asn_org || ''})` : 'N/A'}</span>
                </div>
              </div>

              <div className="detail-section">
                <h3>Proxy/VPN Detection</h3>
                <div className="detail-row">
                  <span className="detail-label">Proxy:</span>
                  <span className="detail-value">{data.is_proxy ? '✅ Yes' : '❌ No'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">VPN:</span>
                  <span className="detail-value">{data.is_vpn ? '✅ Yes' : '❌ No'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Tor:</span>
                  <span className="detail-value">{data.is_tor ? '✅ Yes' : '❌ No'}</span>
                </div>
              </div>

              <div className="detail-section">
                <h3>Metadata</h3>
                <div className="detail-row">
                  <span className="detail-label">Provider:</span>
                  <span className="detail-value">{data.provider || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Last Checked:</span>
                  <span className="detail-value">{data.last_checked ? new Date(data.last_checked).toLocaleString() : 'N/A'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button onClick={handleForceCheck} className="btn btn-warning" disabled={loading}>
            🔄 Force Re-check
          </button>
          <button onClick={onClose} className="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  );
}

function ThreatPanel() {
  const [stats, setStats] = useState(null);
  const [topMalicious, setTopMalicious] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIP, setSelectedIP] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [statsData, topData] = await Promise.all([
        getIPReputationStats(),
        getTopMaliciousIPs(20),
      ]);
      setStats(statsData);
      setTopMalicious(topData.top_malicious_ips || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  const getStatusBadge = (score) => {
    if (score >= 70) return <span className="status-badge malicious">MALICIOUS</span>;
    if (score >= 30) return <span className="status-badge suspicious">SUSPICIOUS</span>;
    return <span className="status-badge safe">SAFE</span>;
  };

  if (loading && !stats) {
    return (
      <div className="card">
        <div className="card-header">
          <span className="card-icon">🛡️</span>
          <h2>Threat Intelligence</h2>
        </div>
        <div className="card-body">
          <div className="loading-inline"><div className="spinner-sm"></div> Loading threat data...</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="card card-wide">
        <div className="card-header">
          <span className="card-icon">🛡️</span>
          <h2>Threat Intelligence</h2>
          <div className="header-controls">
            <label className="auto-refresh-toggle">
              <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
              <span className="toggle-label">Auto</span>
            </label>
            <button onClick={fetchData} className="btn btn-sm" title="Refresh">🔄</button>
          </div>
        </div>
        <div className="card-body">
          {error && <div className="error-message">⚠️ {error}</div>}

          {/* Threat Summary Cards */}
          <div className="threat-summary-grid">
            <div className="threat-stat-card malicious-bg">
              <div className="threat-stat-value">{stats?.malicious_count || 0}</div>
              <div className="threat-stat-label">Malicious IPs</div>
            </div>
            <div className="threat-stat-card suspicious-bg">
              <div className="threat-stat-value">{stats?.suspicious_count || 0}</div>
              <div className="threat-stat-label">Suspicious IPs</div>
            </div>
            <div className="threat-stat-card warning-bg">
              <div className="threat-stat-value">{stats?.malicious_percentage?.toFixed(1) || 0}%</div>
              <div className="threat-stat-label">Malicious Traffic</div>
            </div>
            <div className="threat-stat-card info-bg">
              <div className="threat-stat-value">{stats?.flagged_count || 0}</div>
              <div className="threat-stat-label">Proxy/VPN/Tor Flagged</div>
            </div>
            <div className="threat-stat-card default-bg">
              <div className="threat-stat-value">{stats?.total_ips_checked || 0}</div>
              <div className="threat-stat-label">Total IPs Checked</div>
            </div>
            <div className="threat-stat-card default-bg">
              <div className="threat-stat-value">{stats?.average_abuse_score || 0}</div>
              <div className="threat-stat-label">Avg Abuse Score</div>
            </div>
          </div>

          {/* Top Countries */}
          {stats?.top_countries && stats.top_countries.length > 0 && (
            <div className="geo-section">
              <h3>🌍 Traffic by Country</h3>
              <div className="country-list">
                {stats.top_countries.map((c, i) => (
                  <div key={i} className="country-item">
                    <span className="country-flag">{c.country}</span>
                    <div className="country-bar-container">
                      <div className="country-bar" style={{
                        width: `${Math.min(100, (c.count / Math.max(...stats.top_countries.map(x => x.count))) * 100)}%`
                      }}></div>
                    </div>
                    <span className="country-count">{c.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Malicious IPs Table */}
          <div className="malicious-table-section">
            <h3>🚨 Top Malicious IPs</h3>
            {topMalicious.length === 0 ? (
              <p className="no-data">No malicious IPs detected yet</p>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>IP Address</th>
                      <th>Abuse Score</th>
                      <th>Country</th>
                      <th>Status</th>
                      <th>Threat Flags</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topMalicious.map((item, i) => (
                      <tr key={i} className={item.is_malicious ? 'row-malicious' : item.abuse_score >= 30 ? 'row-suspicious' : ''}>
                        <td className="ip-cell">{item.ip}</td>
                        <td>
                          <div className="score-cell">
                            <div className="score-mini-bar" style={{
                              width: `${item.abuse_score}%`,
                              backgroundColor: item.abuse_score >= 70 ? '#ef4444' : item.abuse_score >= 30 ? '#f59e0b' : '#22c55e'
                            }}></div>
                            <span>{item.abuse_score}</span>
                          </div>
                        </td>
                        <td>{item.country || '—'}</td>
                        <td>{getStatusBadge(item.abuse_score)}</td>
                        <td>
                          {item.threat_flags && item.threat_flags.length > 0
                            ? item.threat_flags.slice(0, 3).map((f, j) => <span key={j} className="threat-flag-sm">{f}</span>)
                            : <span className="text-muted">—</span>}
                        </td>
                        <td>
                          <button
                            className="btn btn-sm btn-outline"
                            onClick={() => setSelectedIP(item.ip)}
                            title="View Details"
                          >
                            🔍
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* IP Details Modal */}
      {selectedIP && (
        <IPDetailsModal ip={selectedIP} onClose={() => setSelectedIP(null)} />
      )}
    </>
  );
}

export { ThreatPanel, IPDetailsModal };
export default ThreatPanel;