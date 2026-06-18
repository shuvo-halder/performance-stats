import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  getMetricsCurrent,
  getMetricsHistory,
  getNetworkDeep,
  getDiskIOPS,
} from '../api';

const API_BASE = process.env.REACT_APP_API_URL || '';

// ── Utility ─────────────────────────────────────────────────────────
const formatBytes = (b) => {
  if (!b || b === 0) return '0 B';
  const k = 1024;
  const s = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return parseFloat((b / Math.pow(k, i)).toFixed(1)) + ' ' + s[i];
};

const formatNumber = (n) => {
  if (n === null || n === undefined) return '—';
  if (n > 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n > 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toFixed ? n.toFixed(1) : n.toString();
};

const percentColor = (p) => {
  if (p >= 80) return '#ef4444';
  if (p >= 60) return '#f59e0b';
  return '#22c55e';
};

// ── SVG Sparkline ─────────────────────────────────────────────────
function Sparkline({ data, color = '#3b82f6', height = 30, smooth = true }) {
  if (!data || data.length < 2) return <div className="sparkline-empty" style={{ height }} />;
  const w = 120, h = height, pad = 2;
  const vals = data.map(d => d.v !== undefined ? d.v : d);
  const maxV = Math.max(...vals, 1);
  const minV = Math.min(...vals, 0);
  const range = maxV - minV || 1;
  const cw = w - pad * 2, ch = h - pad * 2;
  const pts = vals.map((v, i) => {
    const x = pad + (i / (vals.length - 1)) * cw;
    const y = pad + ch - ((v - minV) / range) * ch;
    return `${x},${y}`;
  });
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
  const last = vals[vals.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="grafana-sparkline">
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <text x={w - 5} y={h - 3} fontSize="8" fill="#94a3b8" textAnchor="end">{typeof last === 'number' ? last.toFixed(1) : last}</text>
    </svg>
  );
}

// ── Mini Bar ──────────────────────────────────────────────────────
function MiniBar({ value, max = 100, color, label, suffix = '%', showValue = true }) {
  const pct = Math.min(100, (value / max) * 100);
  const c = color || percentColor(pct);
  return (
    <div className="grafana-minibar">
      {label && <div className="minibar-label">{label}</div>}
      <div className="minibar-track">
        <div className="minibar-fill" style={{ width: `${pct}%`, backgroundColor: c }} />
      </div>
      {showValue && <div className="minibar-value" style={{ color: c }}>{formatNumber(value)}{suffix}</div>}
    </div>
  );
}

// ── Time-Series Area Chart ────────────────────────────────────────
function AreaChart({ data, color = '#3b82f6', height = 80, label = '', smooth = true }) {
  if (!data || data.length < 2) return <div className="chart-placeholder" style={{ height }}>No data</div>;
  const w = 400;
  const vals = data.map(d => d.v !== undefined ? d.v : d);
  const maxV = Math.max(...vals, 1);
  const minV = Math.min(...vals, 0);
  const range = maxV - minV || 1;
  const pad = { t: 12, r: 5, b: 15, l: 5 };
  const cw = w - pad.l - pad.r, ch = height - pad.t - pad.b;
  const pts = vals.map((v, i) => {
    const x = pad.l + (i / (vals.length - 1)) * cw;
    const y = pad.t + ch - ((v - minV) / range) * ch;
    return `${x},${y}`;
  });
  const lineD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
  const areaD = lineD + ` L${pad.l + cw},${pad.t + ch} L${pad.l},${pad.t + ch} Z`;
  const lastVal = vals[vals.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="grafana-chart">
      <defs>
        <linearGradient id={`grad-${label.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <text x={pad.l} y={pad.t - 2} fontSize="9" fill="#64748b">{maxV.toFixed(1)}</text>
      <text x={pad.l} y={height - 2} fontSize="9" fill="#64748b">{minV.toFixed(1)}</text>
      <path d={areaD} fill={`url(#grad-${label.replace(/\s/g, '')})`} />
      <path d={lineD} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <text x={w - pad.r} y={pad.t + 10} fontSize="9" fill="#94a3b8" textAnchor="end">{label}</text>
    </svg>
  );
}

// ── Pie Chart ─────────────────────────────────────────────────────
function MiniPie({ segments, size = 100 }) {
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  if (total === 0) return <div className="chart-placeholder" style={{ height: size }}>No data</div>;
  const cx = size / 2, cy = size / 2, r = size / 2 - 5;
  let cumPct = 0;
  const paths = segments.filter(s => s.value > 0).map(s => {
    const start = (cumPct / 100) * 360;
    cumPct += (s.value / total) * 100;
    const end = (cumPct / 100) * 360;
    const x1 = cx + r * Math.cos((start - 90) * Math.PI / 180);
    const y1 = cy + r * Math.sin((start - 90) * Math.PI / 180);
    const x2 = cx + r * Math.cos((end - 90) * Math.PI / 180);
    const y2 = cy + r * Math.sin((end - 90) * Math.PI / 180);
    const large = (end - start) > 180 ? 1 : 0;
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
    return { ...s, d };
  });
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="grafana-pie">
      {paths.map((p, i) => <path key={i} d={p.d} fill={p.color} stroke="#1e293b" strokeWidth="1" />)}
      <text x={cx} y={cy} textAnchor="middle" fontSize="11" fill="#e2e8f0" fontWeight="bold">{total}</text>
    </svg>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────
export default function GrafanaDashboard() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [mode, setMode] = useState('ema'); // 'raw', 'ema', 'rolling'
  const [period, setPeriod] = useState('1h');
  const [wsConnected, setWsConnected] = useState(false);
  const [connStates, setConnStates] = useState({});
  const [diskData, setDiskData] = useState(null);
  const [rpsHistory, setRpsHistory] = useState([]);
  const [cpuHistory, setCpuHistory] = useState([]);
  const [memHistory, setMemHistory] = useState([]);
  const wsRef = useRef(null);

  // Fetch initial data
  const fetchData = useCallback(async () => {
    try {
      const m = await getMetricsCurrent();
      setData(m);
      if (m.network_deep?.connection_states) setConnStates(m.network_deep.connection_states);
      if (m.disk_iops) setDiskData(m.disk_iops);

      // Build history arrays from smoothed data
      const s = m.smoothed || {};
      const getVal = (key) => {
        if (mode === 'raw') return m.raw?.[key];
        if (mode === 'rolling') return s[key]?.rolling;
        return s[key]?.ema || s[key]?.raw;
      };
      const cpu = getVal('cpu_usage_percent') || m.raw?.cpu_usage_percent || 0;
      const mem = getVal('mem_usage_percent') || m.raw?.mem_usage_percent || 0;
      setCpuHistory(prev => [...prev.slice(-119), cpu]);
      setMemHistory(prev => [...prev.slice(-119), mem]);
    } catch (e) { /* ignore */ }
  }, [mode]);

  const fetchHistory = useCallback(async () => {
    try { const h = await getMetricsHistory(period); setHistory(h.data || []); } catch (e) { /* ignore */ }
  }, [period]);

  useEffect(() => { fetchData(); fetchHistory(); }, [fetchData, fetchHistory]);
  useEffect(() => { const t = setInterval(() => fetchData(), 3000); return () => clearInterval(t); }, [fetchData]);

  // WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = API_BASE ? API_BASE.replace(/^https?:\/\//, '') : window.location.host;
    const url = `${protocol}//${host}/ws/metrics`;
    let reconnect = null;
    let active = true;
    function connect() {
      if (!active) return;
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;
        ws.onopen = () => { if (active) setWsConnected(true); };
        ws.onmessage = (e) => {
          if (!active) return;
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'metrics_snapshot' && msg.data) {
              setData(msg.data);
              if (msg.data.smoothed) {
                const s = msg.data.smoothed;
                const getVal = (key) => {
                  if (mode === 'raw') return msg.data.raw?.[key];
                  if (mode === 'rolling') return s[key]?.rolling;
                  return s[key]?.ema || s[key]?.raw;
                };
                const cpu = getVal('cpu_usage_percent') || 0;
                const mem = getVal('mem_usage_percent') || 0;
                setCpuHistory(prev => [...prev.slice(-119), cpu]);
                setMemHistory(prev => [...prev.slice(-119), mem]);
              }
              if (msg.data.network_deep?.connection_states) setConnStates(msg.data.network_deep.connection_states);
              if (msg.data.disk_iops) setDiskData(msg.data.disk_iops);
            }
          } catch (e) { /* ignore */ }
        };
        ws.onclose = () => { if (active) { setWsConnected(false); reconnect = setTimeout(connect, 3000); } };
        ws.onerror = () => ws.close();
      } catch (e) { reconnect = setTimeout(connect, 5000); }
    }
    connect();
    return () => { active = false; if (reconnect) clearTimeout(reconnect); if (wsRef.current) wsRef.current.close(); };
  }, [mode]);

  const raw = data?.raw || {};
  const smoothed = data?.smoothed || {};
  const net = data?.network_deep || {};
  const disk = data?.disk_iops || {};

  const getVal = (key, fallback = 0) => {
    if (mode === 'raw') return raw[key] ?? fallback;
    if (mode === 'rolling') return smoothed[key]?.rolling ?? raw[key] ?? fallback;
    return smoothed[key]?.ema ?? smoothed[key]?.raw ?? raw[key] ?? fallback;
  };

  const cpuPct = getVal('cpu_usage_percent');
  const memPct = getVal('mem_usage_percent');
  const load1 = getVal('cpu_load_1min');
  const load5 = getVal('cpu_load_5min');
  const load15 = getVal('cpu_load_15min');

  const stateColors = { ESTABLISHED: '#22c55e', TIME_WAIT: '#f59e0b', CLOSE_WAIT: '#ef4444', LISTEN: '#3b82f6', SYN_SENT: '#a78bfa', LAST_ACK: '#f97316' };
  const stateSegments = Object.entries(connStates).map(([k, v]) => ({ label: k, value: v, color: stateColors[k] || '#64748b' }));

  return (
    <div className="grafana-dashboard">
      {/* Header */}
      <div className="grafana-header">
        <div className="grafana-header-left">
          <h1 className="grafana-title">
            <span className="grafana-logo">◆</span> Server Monitor
          </h1>
          <span className="grafana-hostname">{raw.hostname || 'localhost'}</span>
        </div>
        <div className="grafana-header-right">
          <span className={`ws-dot ${wsConnected ? 'connected' : 'disconnected'}`} />
          <span className="ws-label">{wsConnected ? 'LIVE' : 'Polling'}</span>
          <div className="mode-toggle">
            {['raw', 'rolling', 'ema'].map(m => (
              <button key={m} className={`mode-btn ${mode === m ? 'active' : ''}`} onClick={() => setMode(m)}>
                {m === 'raw' ? 'RAW' : m === 'ema' ? 'SMOOTH' : 'AVG'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Section 1: Quick Stats ──────────────────────────────────── */}
      <div className="grafana-quick-stats">
        <div className="grafana-stat-card cpu-pressure">
          <div className="stat-label">CPU Pressure</div>
          <div className="stat-value" style={{ color: percentColor(cpuPct) }}>{formatNumber(cpuPct)}<span className="stat-unit">%</span></div>
          <Sparkline data={cpuHistory} color={percentColor(cpuPct)} height={28} />
        </div>
        <div className="grafana-stat-card">
          <div className="stat-label">CPU Busy</div>
          <div className="stat-value" style={{ color: percentColor(cpuPct) }}>{formatNumber(cpuPct)}%</div>
          <div className="stat-sub">Load: {load1.toFixed(2)}</div>
        </div>
        <div className="grafana-stat-card">
          <div className="stat-label">System Load</div>
          <div className="stat-value">{load1.toFixed(2)}</div>
          <div className="stat-sub">5m: {load5.toFixed(2)} · 15m: {load15.toFixed(2)}</div>
        </div>
        <div className="grafana-stat-card">
          <div className="stat-label">RAM Used</div>
          <div className="stat-value" style={{ color: percentColor(memPct) }}>{formatNumber(memPct)}%</div>
          <div className="stat-sub">{formatBytes((raw.mem_used_mb || 0) * 1e6)} / {formatBytes((raw.mem_total_mb || 1) * 1e6)}</div>
        </div>
        <div className="grafana-stat-card">
          <div className="stat-label">CPU Cores</div>
          <div className="stat-value">{raw.cpu_cores || '—'}</div>
        </div>
        <div className="grafana-stat-card">
          <div className="stat-label">Uptime</div>
          <div className="stat-value stat-small">{raw.uptime || '—'}</div>
        </div>
      </div>

      {/* ── Section 2: Charts Grid ──────────────────────────────────── */}
      <div className="grafana-charts-grid">
        {/* CPU Graph */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">🔲</span>
            <span className="panel-title">CPU Usage</span>
            <span className="panel-value">{cpuPct.toFixed(1)}%</span>
          </div>
          <div className="panel-body">
            <MiniBar value={cpuPct} color={percentColor(cpuPct)} label="Busy" />
            <div className="panel-details">
              <span>User · System · IOWait</span>
            </div>
            {cpuHistory.length > 1 && <AreaChart data={cpuHistory} color={percentColor(cpuPct)} height={70} label={mode.toUpperCase()} />}
          </div>
        </div>

        {/* Memory Graph */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">🧠</span>
            <span className="panel-title">Memory</span>
            <span className="panel-value">{memPct.toFixed(1)}%</span>
          </div>
          <div className="panel-body">
            <MiniBar value={memPct} color={percentColor(memPct)} label="Used" />
            <div className="panel-details">
              <span>Used: {formatBytes((raw.mem_used_mb || 0) * 1e6)}</span>
              <span>Free: {formatBytes((raw.mem_free_mb || 0) * 1e6)}</span>
              <span>Total: {formatBytes((raw.mem_total_mb || 0) * 1e6)}</span>
            </div>
            {memHistory.length > 1 && <AreaChart data={memHistory} color="#22c55e" height={70} label={mode.toUpperCase()} />}
          </div>
        </div>

        {/* Network Graph */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">🌐</span>
            <span className="panel-title">Network</span>
            <span className="panel-value">{net.total_connections || 0}</span>
          </div>
          <div className="panel-body">
            <div className="network-stats">
              <div className="net-stat"><span className="net-label">Active Connections</span><span className="net-value">{net.total_connections || 0}</span></div>
              <div className="net-stat"><span className="net-label">Connection Rate</span><span className="net-value">{net.connection_rate || 0}/s</span></div>
              <div className="net-stat"><span className="net-label">TCP Connections</span><span className="net-value">{raw.network_connections || 0}</span></div>
            </div>
          </div>
        </div>

        {/* Disk Usage */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">💾</span>
            <span className="panel-title">Disk Usage</span>
          </div>
          <div className="panel-body">
            {raw.disk_data?.map((d, i) => (
              <MiniBar key={i} value={d.usage_percent} color={percentColor(d.usage_percent)} label={d.mount} suffix="%" />
            ))}
            {(!raw.disk_data || raw.disk_data.length === 0) && <div className="chart-placeholder">No disk data</div>}
          </div>
        </div>
      </div>

      {/* ── Section 3: Deep Network + Disk IOPS ──────────────────────── */}
      <div className="grafana-charts-grid">
        {/* Connection States Pie */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">🔗</span>
            <span className="panel-title">Connection States</span>
          </div>
          <div className="panel-body panel-body-center">
            {stateSegments.length > 0 ? (
              <div className="pie-with-legend">
                <MiniPie segments={stateSegments} size={100} />
                <div className="pie-legend">
                  {stateSegments.slice(0, 6).map((s, i) => (
                    <div key={i} className="legend-row">
                      <span className="legend-dot" style={{ backgroundColor: s.color }} />
                      <span className="legend-label">{s.label}</span>
                      <span className="legend-value">{s.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <div className="chart-placeholder">No connection data</div>}
          </div>
        </div>

        {/* Top Connected IPs */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">🌍</span>
            <span className="panel-title">Top Network IPs</span>
          </div>
          <div className="panel-body">
            {net.top_ips?.length > 0 ? (
              <div className="grafana-table">
                <div className="grafana-table-header">
                  <span>IP</span>
                  <span>Connections</span>
                </div>
                {net.top_ips.slice(0, 8).map((item, i) => (
                  <div key={i} className="grafana-table-row">
                    <span className="grafana-ip">{item.ip}</span>
                    <span className="grafana-count">{item.count}</span>
                  </div>
                ))}
              </div>
            ) : <div className="chart-placeholder">No IP data</div>}
          </div>
        </div>

        {/* Port Usage */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">🔌</span>
            <span className="panel-title">Busiest Ports</span>
          </div>
          <div className="panel-body">
            {net.port_counts?.length > 0 ? (
              <div className="grafana-table">
                <div className="grafana-table-header">
                  <span>Port</span>
                  <span>Connections</span>
                </div>
                {net.port_counts.slice(0, 8).map((item, i) => (
                  <div key={i} className="grafana-table-row">
                    <span className="grafana-port">{item.port}</span>
                    <span className="grafana-count">{item.count}</span>
                  </div>
                ))}
              </div>
            ) : <div className="chart-placeholder">No port data</div>}
          </div>
        </div>

        {/* Disk IOPS */}
        <div className="grafana-panel">
          <div className="panel-header">
            <span className="panel-icon">⚡</span>
            <span className="panel-title">Disk IOPS</span>
          </div>
          <div className="panel-body">
            {disk.read_iops !== undefined ? (
              <>
                <div className="iops-grid">
                  <div className="iops-stat">
                    <div className="iops-label">Read IOPS</div>
                    <div className="iops-value" style={{ color: '#3b82f6' }}>{formatNumber(disk.read_iops)}</div>
                  </div>
                  <div className="iops-stat">
                    <div className="iops-label">Write IOPS</div>
                    <div className="iops-value" style={{ color: '#f59e0b' }}>{formatNumber(disk.write_iops)}</div>
                  </div>
                  <div className="iops-stat">
                    <div className="iops-label">Read MB/s</div>
                    <div className="iops-value">{disk.read_mb_s?.toFixed(2)}</div>
                  </div>
                  <div className="iops-stat">
                    <div className="iops-label">Write MB/s</div>
                    <div className="iops-value">{disk.write_mb_s?.toFixed(2)}</div>
                  </div>
                </div>
                {disk.devices?.length > 0 && (
                  <div className="disk-devices">
                    <div className="grafana-table">
                      <div className="grafana-table-header">
                        <span>Device</span>
                        <span>R/s</span>
                        <span>W/s</span>
                      </div>
                      {disk.devices.map((d, i) => (
                        <div key={i} className="grafana-table-row">
                          <span className="grafana-ip">{d.device}</span>
                          <span>{d.read_iops}</span>
                          <span>{d.write_iops}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : <div className="chart-placeholder">No IOPS data</div>}
          </div>
        </div>
      </div>

      {/* ── Section 4: History Chart ─────────────────────────────────── */}
      {history.length > 1 && (
        <div className="grafana-panel grafana-panel-wide">
          <div className="panel-header">
            <span className="panel-icon">📈</span>
            <span className="panel-title">History ({period})</span>
            <div className="period-selector">
              {['15m', '1h', '6h', '24h'].map(p => (
                <button key={p} className={`period-btn ${period === p ? 'active' : ''}`} onClick={() => setPeriod(p)}>{p}</button>
              ))}
            </div>
          </div>
          <div className="panel-body">
            <div className="history-panels">
              <div className="history-item">
                <h4>CPU %</h4>
                <AreaChart data={history.map(h => h.cpu_usage_percent || 0)} color="#3b82f6" height={60} label="CPU" />
              </div>
              <div className="history-item">
                <h4>Memory %</h4>
                <AreaChart data={history.map(h => h.mem_usage_percent || 0)} color="#22c55e" height={60} label="MEM" />
              </div>
              <div className="history-item">
                <h4>Connections</h4>
                <AreaChart data={history.map(h => h.network_connections || 0)} color="#a78bfa" height={60} label="NET" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Loading State ────────────────────────────────────────────── */}
      {!data && (
        <div className="grafana-loading">
          <div className="grafana-spinner" />
          <p>Collecting system metrics...</p>
        </div>
      )}
    </div>
  );
}