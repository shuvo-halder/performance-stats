# Installation & Deployment Guide

**Server Stats Monitor v2.0.0** - Production-Grade Server Performance Monitoring Tool

## Table of Contents

- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Scheduling](#scheduling)
- [Alert Setup](#alert-setup)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)
- [Performance & Security](#performance--security)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/shuvo-halder/performance-stats.git
cd performance-stats

# Make script executable
chmod +x server-stats.sh

# Run basic monitoring
./server-stats.sh

# Show help
./server-stats.sh --help

# JSON output
./server-stats.sh --json

# Monitor specific services
./server-stats.sh -s nginx,postgres,redis
```

---

## Installation Methods

### Method 1: Local Installation

```bash
# Clone repository
git clone https://github.com/shuvo-halder/performance-stats.git
cd performance-stats

# Make executable
chmod +x server-stats.sh

# Test execution
./server-stats.sh
```

### Method 2: System-Wide Installation

```bash
# Copy to /usr/local/bin
sudo cp server-stats.sh /usr/local/bin/server-stats
sudo cp server-stats.conf /etc/server-stats.conf
sudo chmod +x /usr/local/bin/server-stats
sudo chmod 644 /etc/server-stats.conf

# Now run from anywhere
server-stats
```

### Method 3: Root Installation (Recommended for Service Management)

```bash
# Copy files
sudo cp server-stats.sh /usr/local/sbin/server-stats
sudo cp server-stats.conf /etc/server-stats.conf
sudo mkdir -p /var/log/server-stats
sudo chown root:root /usr/local/sbin/server-stats
sudo chmod 750 /usr/local/sbin/server-stats
sudo chmod 644 /etc/server-stats.conf
sudo chmod 755 /var/log/server-stats

# Create sudo rule (optional)
sudo tee /etc/sudoers.d/server-stats > /dev/null <<'EOF'
%sysadmin ALL=(ALL) NOPASSWD: /usr/local/sbin/server-stats
EOF
sudo chmod 440 /etc/sudoers.d/server-stats
```

### Method 4: Docker Installation

See [Docker Deployment](#docker-deployment) section.

---

## Configuration

### Basic Configuration File

Edit `/etc/server-stats.conf` or `./server-stats.conf`:

```bash
# Performance thresholds
CPU_THRESHOLD=80          # % CPU usage
MEM_THRESHOLD=85          # % Memory usage
DISK_THRESHOLD=90         # % Disk usage

# Services to monitor
SERVICES=("nginx" "docker" "mysql" "postgresql")

# Auto-restart settings
AUTO_RESTART_FAILED_SERVICES=true
RESTART_ATTEMPTS=3
RESTART_DELAY=5

# Logging
LOG_DIR="/var/log/server-stats"
LOG_ROTATION_SIZE=$((10 * 1024 * 1024))  # 10MB

# Alerts
ENABLE_ALERTS=true
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
EMAIL_RECIPIENT="admin@example.com"

# Output
OUTPUT_JSON=false
VERBOSE=false
```

### Environment Variables

```bash
# Override config file settings via environment
export CPU_THRESHOLD=75
export ENABLE_ALERTS=true
./server-stats.sh
```

---

## Scheduling

### Option 1: Cron Job (Every 10 minutes)

```bash
# Edit crontab
crontab -e

# Add this line
*/10 * * * * /usr/local/bin/server-stats --json -o /var/log/server-stats/latest.json 2>&1 | logger -t server-stats
```

### Option 2: Systemd Timer (Recommended)

Create `/etc/systemd/system/server-stats.service`:

```ini
[Unit]
Description=Server Stats Monitor
Documentation=https://github.com/shuvo-halder/performance-stats
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/sbin/server-stats --json -o /var/log/server-stats/latest.json
StandardOutput=journal
StandardError=journal
SyslogIdentifier=server-stats
```

Create `/etc/systemd/system/server-stats.timer`:

```ini
[Unit]
Description=Server Stats Monitor Timer
Documentation=https://github.com/shuvo-halder/performance-stats
Requires=server-stats.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
AccuracySec=1min

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable server-stats.timer
sudo systemctl start server-stats.timer

# Verify
sudo systemctl status server-stats.timer
sudo systemctl list-timers server-stats.timer
```

### Option 3: Background Daemon

Create a simple monitoring loop:

```bash
#!/bin/bash
# Save as /usr/local/sbin/server-stats-daemon

while true; do
    /usr/local/sbin/server-stats --alerts
    sleep 600  # Run every 10 minutes
done
```

Run as systemd service:

```ini
[Unit]
Description=Server Stats Monitoring Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/sbin/server-stats-daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Alert Setup

### Slack Integration

1. **Create Incoming Webhook:**
   - Go to https://api.slack.com/apps
   - Create New App → "From scratch"
   - Enable "Incoming Webhooks"
   - Add New Webhook to Workspace
   - Copy Webhook URL

2. **Configure:**

```bash
# Edit /etc/server-stats.conf
ENABLE_ALERTS=true
WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXX"

# Or pass via command line
./server-stats.sh --alerts --webhook "https://hooks.slack.com/services/..."
```

### Microsoft Teams Integration

```bash
# Same as Slack - use Teams webhook URL
WEBHOOK_URL="https://outlook.webhook.office.com/webhookb2/..."
./server-stats.sh --alerts --webhook "$WEBHOOK_URL"
```

### Email Alerts

1. **Configure mail service:**

```bash
sudo apt-get install mailutils  # Debian/Ubuntu
# or
sudo yum install mailx           # RHEL/CentOS
```

2. **Configure script:**

```bash
# Edit /etc/server-stats.conf
ENABLE_ALERTS=true
EMAIL_RECIPIENT="admin@example.com"

# Test email
echo "Test" | mail -s "Test Alert" admin@example.com
```

### Custom Webhook

Use any HTTP endpoint that accepts JSON POST:

```bash
# Custom receiver script (Python example)
from flask import Flask, request
import logging

app = Flask(__name__)
logging.basicConfig(filename='alerts.log', level=logging.INFO)

@app.route('/alert', methods=['POST'])
def receive_alert():
    data = request.json
    logging.info(f"Alert: {data['title']} - {data['text']}")
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Configure:

```bash
WEBHOOK_URL="http://your-server:5000/alert"
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    procps \
    util-linux \
    curl \
    mailutils \
    bc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server-stats.sh /app/
COPY server-stats.conf /app/

RUN chmod +x /app/server-stats.sh

ENTRYPOINT ["/app/server-stats.sh"]
CMD ["--help"]
```

### Build & Run

```bash
# Build image
docker build -t server-stats:latest .

# Run once
docker run --rm server-stats:latest

# Run with custom thresholds
docker run --rm server-stats:latest -c 75 -m 80 --json

# Run as daemon with monitoring
docker run -d \
  --name server-stats \
  -v /proc:/proc:ro \
  -v /sys:/sys:ro \
  -v /var/log:/var/log:ro \
  -e CPU_THRESHOLD=75 \
  -e ENABLE_ALERTS=true \
  -e WEBHOOK_URL="https://hooks.slack.com/..." \
  server-stats:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  server-stats:
    build: .
    container_name: server-stats
    restart: always
    volumes:
      - /proc:/proc:ro
      - /sys:/sys:ro
      - /var/log:/var/log:ro
      - ./server-stats.conf:/app/server-stats.conf:ro
      - server-stats-logs:/var/log/server-stats
    environment:
      CPU_THRESHOLD: 75
      MEM_THRESHOLD: 80
      DISK_THRESHOLD: 85
      ENABLE_ALERTS: "true"
      WEBHOOK_URL: "${WEBHOOK_URL}"
      EMAIL_RECIPIENT: "${EMAIL_RECIPIENT}"
    command: --verbose --alerts

volumes:
  server-stats-logs:
```

Run:

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Troubleshooting

### Script doesn't start

```bash
# Check permissions
ls -l server-stats.sh

# Add execute permission
chmod +x server-stats.sh

# Verify bash shebang
head -1 server-stats.sh
# Should output: #!/bin/bash
```

### Lock file error

```bash
# Another instance is running
ps aux | grep server-stats.sh

# Remove stale lock
sudo rm /tmp/server-stats.sh.lock

# Check process and kill if needed
sudo kill -9 <PID>
```

### Permission denied on service restart

```bash
# Allow without password prompt
sudo visudo

# Add this line
%sysadmin ALL=(ALL) NOPASSWD: /usr/local/sbin/server-stats

# Or for specific user
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl
```

### Alerts not sending

```bash
# Test webhook manually
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Check mail service
sudo systemctl status postfix  # or sendmail

# Test email
echo "Test message" | mail -s "Test" admin@example.com
```

### Log rotation issues

```bash
# Check log directory permissions
ls -ld /var/log/server-stats

# Ensure writable
sudo chmod 755 /var/log/server-stats
sudo chown root:root /var/log/server-stats

# Manual rotation
gzip /var/log/server-stats/server-stats.log
```

### High resource usage

```bash
# Monitor script resource usage
time ./server-stats.sh

# Profile with verbose output
./server-stats.sh --verbose 2>&1 | head -50

# Check for hanging processes
ps aux | grep server-stats
```

---

## Performance & Security

### Performance Metrics

| Metric | Value |
|--------|-------|
| CPU Usage | < 1% |
| Memory Footprint | 5-10 MB |
| Execution Time | 2-5 seconds |
| Network I/O | Minimal (unless alerts enabled) |
| Disk I/O | Negligible |
| Log Size/Week | 1-2 MB |

### Security Best Practices

1. **File Permissions:**
```bash
chmod 750 /usr/local/sbin/server-stats
chmod 644 /etc/server-stats.conf
chmod 755 /var/log/server-stats
```

2. **Restrict Execution:**
```bash
# Only root
chmod 700 /usr/local/sbin/server-stats

# Only specific group
chgrp sysadmin /usr/local/sbin/server-stats
chmod 750 /usr/local/sbin/server-stats
```

3. **Webhook URLs:**
- Use HTTPS only
- Rotate tokens regularly
- Use environment variables instead of config files
- Never commit secrets to version control

4. **Logging:**
- Use syslog for centralized logging
- Archive old logs
- Restrict log access (644 or 600)

5. **Systemd Hardening:**

```ini
[Service]
# Restrict execution
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/server-stats

# Resource limits
MemoryLimit=50M
CPUQuota=50%
```

---

## Updates & Maintenance

### Check for Updates

```bash
cd performance-stats
git fetch origin
git log --oneline -n 10
```

### Update Script

```bash
git pull origin main
chmod +x server-stats.sh

# Restart services
sudo systemctl restart server-stats.timer
```

### Backup Configuration

```bash
cp /etc/server-stats.conf /etc/server-stats.conf.backup
```

---

## Support & Resources

- **Repository:** https://github.com/shuvo-halder/performance-stats
- **Issues:** https://github.com/shuvo-halder/performance-stats/issues
- **License:** MIT

---

**Last Updated:** 2026-05-07  
**Version:** 2.0.0
