import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getTrafficLive, getTrafficHistory } from '../api';

const API_BASE = process.env.REACT_APP_API_URL || '';

const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatNumber = (n) => {
  if (!n) return '0';
  if (n > 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n > 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toString();
};

function Sparkline({ data, color = '#3b82f6', height = 40 }) {
  if (!data || data.length < 2) return <div className="chart-placeholder" style={{ height }}>No data</div>;

  const w = 200;
  const h = height;
  const maxV = Math.max(...data, 1);
  const minV = Math.min(...data, 0);
  const range = maxV - minV || 1;
  const padding = 2;
  const chartW = w - padding * 2;
  const chartH = h - padding * 2;

  const points = data.map((v, i) => {
    const x = padding + (i / (data.length - 1)) * chartW;
    const y = padding + chartH - ((v - minV) / range) * chartH;
    return `${x},${y}`;
  });

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
  const lastVal = data[data.length - 1];

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="inline-chart">
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" />
      <text x={w - 45} y={h - 4} fontSize="9" fill="#94a3b8">
        {lastVal.toFixed(1)}
      </text>
    </svg>
  );
}

function StatusCodePie({ counts }) {
  if (!counts) return null;
  const total = (counts['2xx'] || 0) + (counts['3xx'] || 0) + (counts['4xx'] || 0) + (counts['5xx'] || 0);
  if (total === 0) return <p className="no-data">No requests in window</p>;

  const segments = [
    { label: '2xx', value: counts['2xx'] || 0, color: '#22c55e' },
    { label: '3xx', value: counts['3xx'] || 0, color: '#3b82f6' },
    { label: '4xx', value: counts['4xx'] || 0, color: '#f59e0b' },
    { label: '5xx', value: counts['5xx'] || 0, color: '#ef4444' },
  ].filter(s => s.value > 0);

  let cumulativePercent = 0;
  const segPaths = segments.map(s => {
    const startPercent = cumulativePercent;
    cumulativePercent += (s.value / total) * 100;
    return { ...s, startPercent, endPercent: cumulativePercent };
  });

  const w = 120, h = 120, cx = 60, cy = 60, r = 50;

  return (
    <div className="status-pie-container">
      <svg viewBox={`0 0 ${w} ${h}`} className="status-pie">
        {segPaths.map((s, i) => {
          const startAngle = (s.startPercent / 100) * 360;
          const endAngle = (s.endPercent / 100) * 360;
          const x1 = cx + r * Math.cos((startAngle - 90) * Math.PI / 180);
          const y1 = cy + r * Math.sin((startAngle - 90) * Math.PI / 180);
          const x2 = cx + r * Math.cos((endAngle - 90) * Math.PI / 180);
          const y2 = cy + r * Math.sin((endAngle - 90) * Math.PI / 180);
          const largeArc = (s.endPercent - s.startPercent) > 50 ? 1 : 0;
          const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
          return <path key={i} d={d} fill={s.color} stroke="#1e293b" strokeWidth="1" />;
        })}
        <text x={cx} y={cy - 4} textAnchor="middle" fontSize="11" fill="#e2e8f0" fontWeight="bold">{total}</text>
        <text x={cx} y={cy + 8} textAnchor="middle" fontSize="8" fill="#94a3b8">req</text>
      </svg>
      <div className="status-legend">
        {segments.map((s, i) => (
          <div key={i} className="status-legend-item">
            <span className="legend-dot" style={{ backgroundColor: s.color }}></span>
            <span className="legend-label">{s.label}</span>
            <span className="legend-value">{formatNumber(s.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TrafficPanel() {
  const [live, setLive] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyPeriod, setHistoryPeriod] = useState('1h');
  const [rpsHistory, setRpsHistory] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  // Fetch live data via polling (WebSocket fallback)
  const fetchLive = useCallback(async () => {
    try {
      const data = await getTrafficLive();
      setLive(data);
      if (data.rps !== undefined) {
        setRpsHistory(prev => [...prev.slice(-59), data.rps]);
      }
    } catch (err) {
      // silently fail
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await getTrafficHistory(historyPeriod);
      setHistory(data);
    } catch (err) {
      // silently fail
    }
  }, [historyPeriod]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = API_BASE ? API_BASE.replace(/^https?:\/\//, '') : window.location.host;
    const wsUrl = API_BASE
      ? `${protocol}//${host}/ws/traffic`
      : `${protocol}//${window.location.host}/ws/traffic`;

    let reconnectTimer = null;
    let isActive = true;

    function connect() {
      if (!isActive) return;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isActive) setWsConnected(true);
        };

        ws.onmessage = (event) => {
          if (!isActive) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'traffic_snapshot' && msg.data) {
              setLive(msg.data);
              if (msg.data.rps !== undefined) {
                setRpsHistory(prev => [...prev.slice(-59), msg.data.rps]);
              }
            }
          } catch (e) { /* ignore */ }
        };

        ws.onclose = () => {
          if (isActive) {
            setWsConnected(false);
            reconnectTimer = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        if (isActive) {
          reconnectTimer = setTimeout(connect, 5000);
        }
      }
    }

    connect();

    return () => {
      isActive = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Fallback polling if WebSocket fails
  useEffect(() => {
    pollRef.current = setInterval(() => {
      fetchLive();
    }, 5000);
    return () => clearInterval(pollRef.current);
  }, [fetchLive]);

  // Fetch initial data
  useEffect(() => {
    fetchLive();
    fetchHistory();
  }, [fetchLive, fetchHistory]);

  useEffect(() => {
    fetchHistory();
  }, [historyPeriod, fetchHistory]);

  const topIps = live?.top_ips || [];
  const topEndpoints = live?.top_endpoints || [];
  const statusCodes = live?.status_code_counts || {};
  const rps = live?.rps || 0;
  const activeConn = live?.active_connections || 0;
  const errorRate = live?.error_rate || 0;
  const totalRequests = live?.total_requests || 0;
  const bandwidth = live?.bandwidth_bytes || 0;

  return (
    <div className="traffic-panel">
      <div className="card">
        <div className="card-header">
          <span className="card-icon">🚦</span>
          <h2>Live Traffic</h2>
          <div className="ws-status">
            <span className={`status-dot ${wsConnected ? 'green' : 'red'}`}></span>
            {wsConnected ? 'Live' : 'Polling'}
          </div>
          <div className="period-selector">
            {['15m', '1h', '6h', '24h'].map(p => (
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
          <div className="traffic-metrics">
            <div className="traffic-metric">
              <div className="metric-label">Requests/s</div>
              <div className="metric-value">{rps.toFixed(1)}</div>
              <div className="metric-sparkline">
                <Sparkline data={rpsHistory} color="#3b82f6" height={35} />
              </div>
            </div>
            <div className="traffic-metric">
              <div className="metric-label">Active Connections</div>
              <div className="metric-value">{formatNumber(activeConn)}</div>
              <div className="metric-sub">{bandwidth > 0 ? `${formatBytes(bandwidth)}/5s` : ''}</div>
            </div>
            <div className="traffic-metric">
              <div className="metric-label">Error Rate</div>
              <div className={`metric-value ${errorRate > 5 ? 'text-danger' : errorRate > 1 ? 'text-warning' : ''}`}>
                {errorRate}%
              </div>
              <div className="metric-sub">{totalRequests} total requests</div>
            </div>
            <div className="traffic-metric">
              <div className="metric-label">Bandwidth</div>
              <div className="metric-value">{formatBytes(bandwidth)}</div>
              <div className="metric-sub">/ 5s interval</div>
            </div>
          </div>
        </div>
      </div>

      <div className="traffic-grid">
        {/* Top IPs */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">🌍</span>
            <h2>Top IPs</h2>
          </div>
          <div className="card-body">
            {topIps.length > 0 ? (
              <div className="traffic-table">
                <div className="traffic-table-header">
                  <span>#</span>
                  <span>IP Address</span>
                  <span>Requests</span>
                </div>
                {topIps.slice(0, 10).map((item, i) => (
                  <div key={i} className={`traffic-table-row ${item.count > 100 ? 'highlight-flood' : ''}`}>
                    <span className="rank">{i + 1}</span>
                    <span className="ip-addr">{item.ip}</span>
                    <span className="ip-count">{formatNumber(item.count)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No traffic data yet</p>
            )}
          </div>
        </div>

        {/* Top Endpoints */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">🔗</span>
            <h2>Top Endpoints</h2>
          </div>
          <div className="card-body">
            {topEndpoints.length > 0 ? (
              <div className="traffic-table">
                <div className="traffic-table-header">
                  <span>#</span>
                  <span>Endpoint</span>
                  <span>Hits</span>
                </div>
                {topEndpoints.slice(0, 10).map((item, i) => (
                  <div key={i} className="traffic-table-row">
                    <span className="rank">{i + 1}</span>
                    <span className="endpoint-path">{item.endpoint}</span>
                    <span className="ip-count">{formatNumber(item.count)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No endpoint data yet</p>
            )}
          </div>
        </div>

        {/* Status Codes */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">📋</span>
            <h2>Status Codes</h2>
          </div>
          <div className="card-body">
            <StatusCodePie counts={statusCodes} />
          </div>
        </div>

        {/* RPS Chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-icon">📈</span>
            <h2>RPS History</h2>
          </div>
          <div className="card-body">
            {rpsHistory.length > 1 ? (
              <div className="rps-chart">
                <svg viewBox="0 0 400 120" className="traffic-chart">
                  <defs>
                    <linearGradient id="rpsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <text x="5" y="15" fontSize="9" fill="#94a3b8">{Math.max(...rpsHistory, 1).toFixed(1)}</text>
                  <text x="5" y="115" fontSize="9" fill="#94a3b8">0</text>
                  {(() => {
                    const maxV = Math.max(...rpsHistory, 1);
                    const minV = Math.min(...rpsHistory, 0);
                    const range = maxV - minV || 1;
                    const chartW = 390, chartH = 100, padL = 10, padT = 5;
                    const points = rpsHistory.map((v, i) => {
                      const x = padL + (i / (rpsHistory.length - 1)) * chartW;
                      const y = padT + chartH - ((v - minV) / range) * chartH;
                      return `${x},${y}`;
                    });
                    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
                    const areaD = pathD + ` L${padL + chartW},${padT + chartH} L${padL},${padT + chartH} Z`;
                    return (
                      <>
                        <path d={areaD} fill="url(#rpsGrad)" />
                        <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="2" />
                      </>
                    );
                  })()}
                </svg>
              </div>
            ) : (
              <p className="no-data">Collecting RPS data...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}