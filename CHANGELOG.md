# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-05-07

### Added
- **JSON Output Support**: Export monitoring data as structured JSON for integration with monitoring systems
- **Webhook Notifications**: Send alerts to Slack, Teams, or custom webhooks
- **Email Alerts**: Send critical alerts via email
- **Persistent Logging**: Structured logging with automatic rotation (max 10MB)
- **Configuration File**: `server-stats.conf` for easy deployment customization
- **Lock File Mechanism**: Prevent multiple concurrent instances
- **Enhanced Error Handling**: Comprehensive error handling and validation
- **Improved Command-Line Interface**: Full argument parsing with help documentation
- **Metric Collection**: Store and export all metrics for analysis
- **Production-Grade Features**:
  - Proper exit codes and error handling
  - Signal handling (INT, TERM)
  - Timestamp logging for all events
  - Verbose logging to file
  - Service restart with retry logic
  - Threshold validation

### Improved
- Better code organization and structure
- Enhanced security checks
- More robust network information gathering
- Improved CPU and memory usage calculation accuracy
- Better handling of missing commands
- Enhanced process monitoring

### Changed
- Command-line argument format (now supports long options)
- Configuration management (centralized in `server-stats.conf`)
- Output formatting (consistent with professional standards)

### Fixed
- Handle edge cases in disk and memory calculations
- Better error recovery for systemctl operations
- Improved handling of systems without certain utilities
- Better validation of user inputs

## [1.0.0] - 2026-01-09

### Initial Release
- Basic server performance monitoring
- CPU, Memory, Disk monitoring
- Service status checking
- Auto-restart failed services capability
- Security check functionality
- Top processes monitoring
- Basic colored output

---

## Installation

```bash
# Clone repository
git clone https://github.com/shuvo-halder/performance-stats.git
cd performance-stats

# Make script executable
chmod +x server-stats.sh

# Optional: Copy configuration file
cp server-stats.conf /etc/server-stats.conf

# Optional: Create systemd service for scheduled monitoring
sudo tee /etc/systemd/system/server-stats.timer > /dev/null <<EOF
[Unit]
Description=Server Stats Monitor Timer
Requires=server-stats.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
EOF
```

## Usage

```bash
# Basic usage
./server-stats.sh

# Show help
./server-stats.sh --help

# JSON output
./server-stats.sh --json

# Custom thresholds
./server-stats.sh --cpu 75 --memory 80 --disk 85

# With alerts
./server-stats.sh --alerts --webhook https://hooks.slack.com/... --email admin@example.com

# Monitor specific services
./server-stats.sh --services nginx,postgres,redis
```

## Migration Guide (v1 → v2)

### Configuration Changes
- Move custom settings to `server-stats.conf`
- Update threshold values in the config file
- No changes needed for basic functionality

### Command-Line Changes
| Old Format | New Format |
|----------|-----------|
| `-j` | `-j` or `--json` (same) |
| `-o file` | `-o file` or `--output file` |
| `-s services` | `-s services` or `--services services` |
| New | `-c VALUE` or `--cpu VALUE` |
| New | `-m VALUE` or `--memory VALUE` |
| New | `-d VALUE` or `--disk VALUE` |

### Alert Configuration
New in v2! Set up alerts via:
1. Configuration file: `server-stats.conf`
2. Command-line arguments: `--webhook` and `--email`
3. Environment variables

## Performance Impact

- Minimal CPU usage (<1%)
- Memory footprint: ~5-10MB
- Logging overhead: ~1-2MB per week (with rotation)
- Network: Negligible unless webhooks enabled

## Troubleshooting

### Script exits with lock file error
- Another instance is running: `ps aux | grep server-stats.sh`
- Remove stale lock: `sudo rm /tmp/server-stats.sh.lock`

### Alerts not sending
- Verify webhook URL: `curl -X POST $WEBHOOK_URL`
- Check email configuration: `mail -v`
- Review logs: `tail -f /var/log/server-stats/server-stats.log`

### Permission denied for service restart
- Ensure script runs with sudo for service operations
- Or configure sudoers for specific commands

---

**For more information, visit:** https://github.com/shuvo-halder/performance-stats
