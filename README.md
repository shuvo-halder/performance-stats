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
│              ┌─────────▼─────────┐                            │
│              │   SQLite DB       │                            │
│              │  (historical      │                            │
│              │   snapshots)      │                            │
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
│       │   └── security.py     # Failed login attempts
│       └── routers/
│           └── stats.py        # API endpoints
├── frontend/                   # React dashboard
│   ├── package.json
│   ├── Dockerfile              # Multi-stage build (Node → Nginx)
│   ├── nginx.conf              # Nginx config with API proxy
│   └── src/
│       ├── App.js              # Dashboard component
│       ├── api.js              # API client
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