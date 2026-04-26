

# 🖥️ Performance Stats - Advanced Server Monitor

A lightweight, production-ready Bash script to monitor Linux server performance, health, and security with alerting support.

🔗 **GitHub Repo:** [https://github.com/shuvo-halder/performance-stats](https://github.com/shuvo-halder/performance-stats)

---

## 🚀 Features

* ✅ OS, Kernel & Uptime info
* ✅ CPU usage + Load Average + Alerts
* ✅ Memory usage monitoring
* ✅ Disk usage (per mount point)
* ✅ Network stats (connections & ports)
* ✅ Service health check (customizable)
* ✅ Auto-Restart Failed Services
* ✅ Security check (failed SSH logins)
* ✅ Top processes (CPU & Memory)
* ✅ Color-coded output (OK / WARN / ALERT)
* ✅ Save report to file
* ✅ Cron-friendly execution

---

## 📸 Sample Output

```
=======================================
     ADVANCED SERVER MONITOR REPORT
=======================================

--- CPU Info ---
Cores: 4
Load Avg: 0.20, 0.25, 0.30
CPU Usage: 32%
[OK] CPU usage normal

--- Memory Info ---
Used: 1200MB / 4096MB (29.30%)
[OK] Memory usage normal

--- Disk Info ---
[ALERT] Disk high usage on /: 91%
```

---

## 📦 Requirements

* Linux (Ubuntu / Debian / CentOS)
* Bash (v4+)
* Required tools:

  * `awk`
  * `grep`
  * `ps`
  * `ss`
  * `top`
  * `bc`

### Install dependencies (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install procps iproute2 bc
```

---

## ⚙️ Installation

```bash
git clone https://github.com/shuvo-halder/performance-stats.git
cd performance-stats
chmod +x server-stats.sh
```

---

## ▶️ Usage

### 🔹 Run Script

```bash
./server-stats.sh
```

---

### 🔹 Save Output to File

```bash
./server-stats.sh -o report.txt
```

---

### 🔹 Check Specific Services

```bash
./server-stats.sh -s nginx,docker,redis
```

---

### 🔹 Run with Cron (Every 5 Minutes)

```bash
*/5 * * * * /path/to/server-stats.sh >> /var/log/performance-stats.log
```

---

## ⚡ Configuration

Edit thresholds inside the script:

```bash
CPU_THRESHOLD=80
MEM_THRESHOLD=85
DISK_THRESHOLD=90
```

Default services:

```bash
SERVICES=("nginx" "docker" "mysql")
```
---
## 🔄 Auto-Restart Failed Services

The monitoring script can automatically detect stopped services and attempt to restart them. This helps reduce downtime and keeps critical applications running without manual intervention.

### ✅ Features

- Detects inactive or failed services
- Automatically restarts stopped services
- Multiple restart attempts
- Delay between retries
- Clear success / failure logs
- Works with any `systemd` service

```bash
AUTO_RESTART_FAILED_SERVICES=true
RESTART_ATTEMPTS=2
RESTART_DELAY=3

SERVICES=("nginx" "docker" "mysql")
```
---

## 🔐 Security Checks

* Counts failed SSH login attempts
* Displays open ports
* Helps identify brute-force attacks

---

## 🧩 Options

| Option | Description                            |
| ------ | -------------------------------------- |
| `-o`   | Save output to file                    |
| `-s`   | Custom services (comma-separated)      |
| `-j`   | Reserved for JSON output (coming soon) |

---

## 🔮 Roadmap

* 🔔 Telegram / Slack alerts
* 📊 JSON output (API / Prometheus ready)
* 🔄 ~~Auto-restart failed services~~
* 🐳 Docker container monitoring
* 📈 Historical performance tracking

---

## ⚠️ Notes

* Some features require root privileges
* Best suited for VPS / cloud servers
* Tested on Ubuntu & Debian

---

## 🤝 Contributing

Contributions are welcome!

```bash
git checkout -b feature/your-feature
git commit -m "Add new feature"
git push origin feature/your-feature
```

---

## 📜 License

MIT License

---

## 👨‍💻 Author

**Shuvo Halder**
System Engineer | Automation Enthusiast

---

## ⭐ Support

If you find this useful, consider giving it a ⭐ on GitHub!

