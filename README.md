# 🖥️ Server Stats Monitor

**Production-grade server performance monitoring** — from CLI to full-stack dashboard.

Track CPU, memory, disk, network, services, and security metrics in real-time with historical trends and alerting.

🔗 **GitHub:** [https://github.com/shuvo-halder/performance-stats](https://github.com/shuvo-halder/performance-stats)

---

## 🌟 Features

### CLI Mode (Bash Script)
- ✅ OS, Kernel, Uptime info
- ✅ CPU usage + Load Average + Alerts
- ✅ Memory, Disk, Network monitoring
- ✅ Service health check + Auto-restart
- ✅ Security check (failed SSH logins)
- ✅ Top processes (CPU & Memory)
- ✅ Color-coded output, file saving, cron-ready

### API Mode (Python + FastAPI)
- ✅ RESTful JSON API with all metrics
- ✅ API key authentication
- ✅ Background auto-collection (every 60s)
- ✅ SQLite database for historical trends
- ✅ Auto-generated Swagger docs (`/docs`)
- ✅ Threshold-based alert evaluation
- ✅ Docker Compose one-command deploy

### Dashboard Mode (React)
- ✅ Real-time dark-themed dashboard
- ✅ CPU gauge with load averages
- ✅ Memory progress bar + details
- ✅ Per-mount disk usage charts
- ✅ Service status with auto-restart results
- ✅ Network connections & listening ports
- ✅ Top processes tables (CPU & Memory)
- ✅ Historical trend charts (1h / 6h / 24h / 7d)
- ✅ Auto-refresh every 10 seconds

### IP Reputation & Threat Intelligence (v2.1.0)
- ✅ Multi-provider IP reputation lookups (AbuseIPDB, VirusTotal, IPQualityScore)
- ✅ In-memory TTL cache + SQLite persistence for IP reputation data
- ✅ Real-time IP enrichment during traffic processing
- ✅ Abuse score 0–100, country, ISP, ASN, reverse DNS detection
- ✅ Proxy / VPN / Tor / Bot threat flagging
- ✅ 3-tier classification: SAFE → SUSPICIOUS → MALICIOUS
- ✅ Alert generation for malicious IPs, high-RPS bots, proxy detection
- ✅ Async HTTP client (httpx) with rate limiting and retry logic
- ✅ Dedicated Threat Intelligence dashboard panel
- ✅ IP detail modal with force re-check capability
- ✅ Traffic-by-country geo visualization
- ✅ Top malicious IPs table with abuse scores and threat flags

### 🔔 Alert Manager (v3.0 — Tier-1)
- ✅ Configurable alert rules (CPU, memory, disk, load, service, SSL, threat)
- ✅ Multi-channel notifications: Email, Telegram, Discord, Slack, Generic Webhook
- ✅ Alert severity levels: INFO, WARNING, CRITICAL
- ✅ Duplicate prevention with cooldown system
- ✅ Alert acknowledgement and resolution workflow
- ✅ Dedicated Alert Center page with active alerts widget

### 🖥️ Multi-Server & Agent System (v3.0 — Tier-1)
- ✅ Monitor unlimited servers from a central dashboard
- ✅ Per-server metrics: CPU, memory, disk, load, processes, services
- ✅ Auto-registration with secure agent tokens (HMAC-SHA256 signing)
- ✅ Lightweight Python agent with local caching and retry logic
- ✅ One-line Linux installation via `curl | bash`
- ✅ Systemd service with auto-restart
- ✅ Global infrastructure overview (online/offline/warning/critical)

### ⏱️ Uptime Monitor (v3.0 — Tier-1)
- ✅ Monitor HTTP, HTTPS, TCP endpoints
- ✅ Configurable check intervals, timeouts, retries
- ✅ 24/7 availability percentage tracking
- ✅ Incident management with downtime duration
- ✅ Response time monitoring per check

### 🔒 SSL Certificate Monitor (v3.0 — Tier-1)
- ✅ Scan SSL/TLS certificates for any hostname
- ✅ Track expiration dates with days-remaining countdown
- ✅ Color-coded alert levels (30, 15, 7, 3 days)
- ✅ SAN (Subject Alternative Names) extraction
- ✅ Certificate details modal with issuer, subject, algorithm

### ⚙️ Process Monitor (v3.0 — Tier-1)
- ✅ Monitor critical services: nginx, mysql, postgresql, redis, docker, etc.
- ✅ Real-time CPU and memory usage per process
- ✅ Process uptime tracking
- ✅ Auto-restart with configurable max attempts
- ✅ Event history for all state changes

### 📊 Grafana-Inspired Real-Time Dashboard
- ✅ Live CPU pressure sparkline with system load (1m/5m/15m)
- ✅ Memory panel with RAM + Swap usage bars
- ✅ Disk usage per mount point
- ✅ Deep network insight: connection states pie chart, top IPs, busiest ports
- ✅ Disk IOPS monitoring (read/write ops/sec + MB/s)
- ✅ Raw / Rolling Average / EMA smoothing toggle
- ✅ WebSocket real-time updates (2s interval)
- ✅ Historical time-series charts (15m/1h/6h/24h)

### 🚦 Real-Time Traffic Monitoring
- ✅ Nginx/Apache log tailing with sliding window aggregation
- ✅ RPS (requests/sec) with sparkline + area chart
- ✅ Top IPs table with flood highlighting
- ✅ Top endpoints heatmap
- ✅ Status code pie chart (2xx/4xx/5xx)
- ✅ WebSocket push every 2 seconds with polling fallback

---

## 🚀 Quick Start

### Option 1: Docker (Easiest — Everything in One Command)

```bash
# Clone
git clone https://github.com/shuvo-halder/performance-stats.git
cd performance-stats

# Start all services
docker-compose up --build

# Open in your browser:
#   Dashboard → http://localhost:8080
#   API Docs  → http://localhost:8000/docs
```

### Option 2: Backend + Frontend (Manual)

**Backend (Python 3.11+):**
```bash
cd backend
pip install -r backend\requirements.txt
python run.py
# API at http://localhost:8000
```

**Frontend (Node 18+):**
```bash
cd frontend
npm install
npm start
# Dashboard at http://localhost:3000
```

### Option 3: CLI Only (Bash)

```bash
chmod +x server-stats.sh
./server-stats.sh               # Quick overview
./server-stats.sh --json        # JSON output
./server-stats.sh -o report.txt # Save to file
./server-stats.sh -s nginx,docker,redis  # Monitor services
```

---

## 📸 Dashboard Preview

```
┌──────────────────────────────────────────────────────────────────┐
│ 🖥️ Server Monitor    prod-01                    ● Healthy    🔄 │
├───────────┬───────────┬───────────┬──────────────────────────────┤
│  🔲 CPU  │  🧠 Mem   │  💾 Disk  │  ⚙️ Services               │
│  ┌─────┐ │ ████████  │  /: 45%   │  ● nginx   running          │
│  │ 32% │ │  45%      │  /data    │  ● docker  running          │
│  └─────┘ │  4.2/16GB │    78%    │  ● mysql   stopped          │
│  2.4 load│           │           │                              │
├───────────┴───────────┴───────────┴──────────────────────────────┤
│  🌐 Network: 23 active TCP · Ports: 22,80,443,3000              │
├────────────────────────────┬─────────────────────────────────────┤
│  📊 Top CPU               │  📊 Top Memory                     │
│  PID  Name      CPU%      │  PID  Name      MEM%               │
│  1234 node      12.5      │  5678 mysql     8.3                │
│  9012 nginx      5.1      │  3456 postgres   4.2               │
└────────────────────────────┴─────────────────────────────────────┘
```

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      React Dashboard                         │
│                    (port 8080 / 3000)                         │
└───────────────────────────┬───────────────────────────────────┘
                            │ REST API (JSON) + API Key Auth
┌───────────────────────────▼───────────────────────────────────┐
│                   FastAPI Python Backend                      │
│                    (port 8000)                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Collectors (async, run concurrently)                │    │
│  │  ├─ system.py   → OS, kernel, hostname, uptime      │    │
│  │  ├─ cpu.py      → cores, usage %, load averages     │    │
│  │  ├─ memory.py   → total, used, free, usage %        │    │
│  │  ├─ disk.py     → per-mount usage (GB + %)          │    │
│  │  ├─ network.py  → TCP connections, listening ports  │    │
│  │  ├─ services.py → systemctl status + auto-restart   │    │
│  │  ├─ processes.py→ top CPU & memory consumers        │    │
│  │  └─ security.py → failed SSH login attempts         │    │
│  └──────────────────────────────────────────────────────┘    │
│                        │                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  IP Reputation (async, multi-provider)               │    │
│  │  ├─ service.py   → AbuseIPDB, VirusTotal, IPQS      │    │
│  │  ├─ models.py    → SQLite ip_reputation table       │    │
│  │  ├─ router.py    → /ip/* REST endpoints             │    │
│  │  └─ integration.py → enrichment + alerting          │    │
│  └──────────────────────────────────────────────────────┘    │
│                        │                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Tier-1 Feature Modules                             │    │
│  │  ├─ alert_manager/ → rules, channels, lifecycle     │    │
│  │  ├─ multi_server/  → registration, metrics, status  │    │
│  │  ├─ uptime_monitor/→ HTTP/TCP checks, incidents     │    │
│  │  ├─ ssl_monitor/   → cert scanning, expiry tracking │    │
│  │  ├─ process_monitor/→ psutil checks, auto-restart   │    │
│  │  ├─ metrics/       → EMA smoothing, deep network,   │    │
│  │  │                   disk IOPS, background collector│    │
│  │  └─ agent/         → lightweight Python daemon      │    │
│  └──────────────────────────────────────────────────────┘    │
│                        │                                      │
│              ┌─────────▼─────────┐                            │
│              │   SQLite DB       │                            │
│              │  (historical      │                            │
│              │   snapshots,      │                            │
│              │   traffic logs,   │                            │
│              │   ip_reputation,  │                            │
│              │   alerts,         │                            │
│              │   servers,        │                            │
│              │   uptime,         │                            │
│              │   ssl_certs,      │                            │
│              │   processes)      │                            │
│              └───────────────────┘                            │
└───────────────────────────────────────────────────────────────┘

Also available as a standalone Bash script (server-stats.sh) for
terminal-only environments.
```

---

## 📡 API Reference

All endpoints require an API key. Pass it via:
- **Header:** `X-API-Key: your-key`
- **Auth:** `Authorization: Bearer your-key`
- **Query:** `?api_key=your-key`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API root with links to all endpoints |
| `GET` | `/api/stats` | Collect fresh metrics + save to DB + alert check |
| `GET` | `/api/stats/latest` | Most recent saved snapshot |
| `GET` | `/api/stats/history?period=1h` | Historical data (1h, 6h, 24h, 7d) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/config` | Current thresholds & settings |
| `GET` | `/docs` | Swagger UI (interactive API docs) |
| `GET` | `/traffic/live` | Current live traffic snapshot (RPS, IPs, endpoints) |
| `GET` | `/traffic/history?period=1h` | Historical traffic aggregates |
| `WS` | `/ws/traffic` | WebSocket pushing live traffic every 2s |
| `GET` | `/ip/{ip}` | Full IP reputation data (cached or live lookup) |
| `GET` | `/ip/check/{ip}` | Force re-check IP reputation (bypass cache) |
| `GET` | `/ip/top-malicious?limit=20` | Highest risk IPs from recent traffic |
| `GET` | `/ip/stats` | Threat summary: % malicious, top countries, flagged count |
| `POST` | `/ip/batch-check` | Batch check up to 50 IPs at once |
| `GET` | `/metrics/current` | Live dashboard metrics with smoothing (raw/EMA/rolling) |
| `GET` | `/metrics/history?period=1h` | Historical metric snapshots |
| `GET` | `/metrics/network/deep` | Deep network: connection states, top IPs, ports |
| `GET` | `/metrics/disk/iops` | Disk IOPS: read/write ops/sec, throughput |
| `WS` | `/ws/metrics` | WebSocket pushing live metrics every 2s |
| `GET` | `/alerts/rules` | List alert rules |
| `POST` | `/alerts/rules` | Create alert rule |
| `PUT` | `/alerts/rules/{id}` | Update alert rule |
| `DELETE` | `/alerts/rules/{id}` | Delete alert rule |
| `GET` | `/alerts/active` | Active alerts list |
| `GET` | `/alerts/history` | Alert history |
| `POST` | `/alerts/{id}/acknowledge` | Acknowledge alert |
| `POST` | `/alerts/{id}/resolve` | Resolve alert |
| `GET` | `/alerts/channels` | List notification channels |
| `POST` | `/alerts/channels` | Create notification channel |
| `DELETE` | `/alerts/channels/{id}` | Delete notification channel |
| `POST` | `/alerts/channels/{id}/test` | Test notification channel |
| `GET` | `/servers` | List registered servers |
| `GET` | `/servers/summary` | Infrastructure overview (online/offline counts) |
| `POST` | `/servers/register` | Register new server (returns agent token) |
| `POST` | `/servers/metrics?token=` | Push agent metrics |
| `GET` | `/servers/{id}` | Server details with latest metrics |
| `GET` | `/uptime/monitors` | List uptime monitors |
| `POST` | `/uptime/monitors` | Create uptime monitor |
| `PUT` | `/uptime/monitors/{id}` | Update uptime monitor |
| `DELETE` | `/uptime/monitors/{id}` | Delete uptime monitor |
| `POST` | `/uptime/monitors/{id}/check` | Run instant uptime check |
| `GET` | `/uptime/monitors/{id}/history` | Uptime check history |
| `GET` | `/uptime/monitors/{id}/incidents` | Uptime incident list |
| `POST` | `/ssl/scan` | Scan SSL certificate |
| `GET` | `/ssl/certificates` | List SSL certificates |
| `GET` | `/ssl/certificates/{id}` | SSL certificate details |
| `GET` | `/processes` | List monitored processes |
| `POST` | `/processes` | Add process to monitor |
| `DELETE` | `/processes/{id}` | Remove monitored process |
| `POST` | `/processes/{id}/check` | Check process status |
| `POST` | `/processes/check-all` | Check all processes |
| `GET` | `/processes/{id}/events` | Process event history |

### Example

```bash
curl "http://localhost:8000/api/stats?api_key=sk-prod-server-stats-monitor-key-2026"
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2026-06-16T20:00:00Z",
  "hostname": "prod-01",
  "alerts": [],
  "cpu_usage_percent": 32.5,
  "cpu_cores": 8,
  "mem_usage_percent": 45.2,
  "mem_total_mb": 16384,
  "disk_data": [{"mount": "/", "usage_percent": 45, "used_gb": 120, "total_gb": 256}],
  "services_data": [{"name": "nginx", "status": "active"}],
  ...
}
```

---

## ⚙️ Configuration

### Environment Variables (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `sk-prod-...` | API authentication key |
| `CPU_THRESHOLD` | `80` | CPU alert threshold (%) |
| `MEM_THRESHOLD` | `85` | Memory alert threshold (%) |
| `DISK_THRESHOLD` | `90` | Disk alert threshold (%) |
| `SERVICES` | `nginx,docker,mysql` | Services to monitor |
| `COLLECTION_INTERVAL` | `60` | Background collection interval (s) |
| `ABUSEIPDB_API_KEY` | — | AbuseIPDB API key for IP reputation lookups |
| `VIRUSTOTAL_API_KEY` | — | VirusTotal API key for IP reputation lookups |
| `IPQUALITYSCORE_API_KEY` | — | IPQualityScore API key for IP reputation lookups |
| `IP_REPUTATION_CACHE_TTL` | `1800` | Cache TTL for IP reputation (seconds) |
| `IP_REPUTATION_ABUSE_THRESHOLD` | `70` | Abuse score threshold for alerting (0–100) |
| `IP_REPUTATION_MAX_REQUESTS_PER_IP` | `300` | Max requests per IP before alert |
| `IP_REPUTATION_RATE_LIMIT` | `30` | API calls per minute to external providers |

### CLI Script Configuration (`server-stats.conf`)

```bash
CPU_THRESHOLD=80
MEM_THRESHOLD=85
DISK_THRESHOLD=90
SERVICES=("nginx" "docker" "mysql")
```

---

## 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The `docker-compose.yml` spins up:
1. **backend** — FastAPI server (port 8000)
2. **frontend** — React dashboard via Nginx (port 8080)

### Custom Environment

```bash
API_KEY="my-secret-key-123" docker-compose up -d
```

---

## 📂 Project Structure

```
performance-stats/
├── backend/                    # Python FastAPI backend
│   ├── .env.example            # Environment template (copy to .env)
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Backend container
│   ├── run.py                  # Entry point
│   └── app/
│       ├── main.py             # FastAPI app + background scheduler
│       ├── config.py           # Pydantic settings
│       ├── auth.py             # API key authentication
│       ├── database.py         # SQLAlchemy + SQLite models
│       ├── collectors/         # System metric collectors
│       │   ├── cpu.py          # CPU metrics
│       │   ├── memory.py       # Memory metrics
│       │   ├── disk.py         # Disk metrics
│       │   ├── network.py      # Network metrics
│       │   ├── services.py     # Service status + auto-restart
│       │   ├── processes.py    # Top processes
│       │   ├── security.py     # Failed login attempts
│       │   └── traffic.py      # In-memory traffic sliding window
│       ├── ip_reputation/      # Threat Intelligence module
│       │   ├── service.py      # Multi-provider IP lookups + caching
│       │   ├── models.py       # SQLite ip_reputation table
│       │   ├── router.py       # /ip/* FastAPI endpoints
│       │   └── integration.py  # Real-time enrichment + alerting
│       ├── alert_manager/      # Tier-1: Alert rules, channels, lifecycle
│       │   ├── service.py      # Rule evaluation, dedup, notifications
│       │   └── router.py       # /alerts/* endpoints
│       ├── multi_server/       # Tier-1: Multi-server infrastructure
│       │   ├── service.py      # Registration, metrics, status
│       │   └── router.py       # /servers/* endpoints
│       ├── uptime_monitor/     # Tier-1: HTTP/HTTPS/TCP uptime checks
│       │   ├── service.py      # Check logic, incidents, history
│       │   └── router.py       # /uptime/* endpoints
│       ├── ssl_monitor/        # Tier-1: SSL certificate scanning
│       │   ├── service.py      # Async fetch, parsing, expiry
│       │   └── router.py       # /ssl/* endpoints
│       ├── process_monitor/    # Tier-1: Process monitoring + auto-restart
│       │   ├── service.py      # psutil checks, systemctl restart
│       │   └── router.py       # /processes/* endpoints
│       ├── metrics/            # Advanced metrics + real-time dashboard
│       │   ├── smoothing.py    # EMA + rolling average engine
│       │   ├── network_deep.py # Connection states, top IPs, ports
│       │   ├── disk_iops.py    # Read/write IOPS, throughput
│       │   └── router.py       # /metrics/* + /ws/metrics
│       ├── agent/              # Lightweight monitoring agent
│       │   ├── monitor_agent.py# Python daemon with HMAC signing
│       │   └── install.sh      # One-line Linux installer
│       ├── models.py           # All Tier-1 database schemas
│       └── routers/
│           ├── stats.py        # System stats endpoints
│           ├── auth.py         # Authentication endpoints
│           └── traffic.py      # Traffic monitoring + WebSocket
├── frontend/                   # React dashboard
│   ├── package.json
│   ├── Dockerfile              # Multi-stage build (Node → Nginx)
│   ├── nginx.conf              # Nginx config with API proxy
│   └── src/
│       ├── App.js              # Main app with 8-tab navigation
│       ├── api.js              # API client (all endpoints)
│       ├── components/         # React components
│       │   ├── GrafanaDashboard.js  # Real-time metrics dashboard
│       │   ├── AlertCenter.js       # Alert management page
│       │   ├── ServersPage.js       # Server infrastructure page
│       │   ├── UptimePage.js        # Uptime monitor page
│       │   ├── SSLPage.js           # SSL certificate page
│       │   ├── ProcessPage.js       # Process monitor page
│       │   ├── TrafficPanel.js      # Traffic monitoring panel
│       │   ├── ThreatPanel.js       # Threat intelligence panel
│       │   ├── Login.js             # Authentication page
│       │   └── AdminPanel.js        # User management
│       └── styles/             # CSS styles
├── server-stats.sh             # Original Bash script (v2.0.0)
├── server-stats.conf           # Bash script configuration
├── docker-compose.yml          # One-command deployment
├── .gitignore
└── ssh/                        # SSH security setup guide
```

---

## 🔐 API Security

- **Authentication:** API key required on all endpoints
- **Key validation:** Supports headers (`X-API-Key`, `Authorization`) and query params
- **Default key:** Change immediately in production!
  ```bash
  # Generate a secure key
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- **CORS:** Open by default (restrict `allow_origins` in `main.py` for production)

---

## 📊 Tech Stack

| Component | Technology |
|-----------|-----------|
| API Server | Python 3.11+ / FastAPI |
| Database | SQLite (via SQLAlchemy async) |
| Dashboard | React 18 |
| Charts | SVG (built-in) |
| Container | Docker / Docker Compose |
| CLI Script | Bash (standalone) |
| Monitoring | psutil (cross-platform) |

---

## 📜 License

MIT License — Copyright (c) 2026 Shuvo Halder

---

## 👨‍💻 Author

**Shuvo Halder** — System Engineer & Automation Enthusiast

[![GitHub](https://img.shields.io/badge/GitHub-shuvo--halder-blue?style=flat&logo=github)](https://github.com/shuvo-halder)

---

## ⭐ Support

If you find this project useful, please ⭐ star it on GitHub!