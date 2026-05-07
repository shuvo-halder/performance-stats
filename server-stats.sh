#!/bin/bash

################################################################################
#                    PERFORMANCE STATS MONITOR v2.0.0                         #
#              Production-Grade Server Performance Monitoring Tool             #
#                                                                              #
# Description: Lightweight, extensible Bash script for monitoring Linux       #
#              server performance, health, and security with alerts           #
#                                                                              #
# Author: Shuvo Halder                                                        #
# License: MIT                                                                #
# Repository: https://github.com/shuvo-halder/performance-stats               #
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION & INITIALIZATION
# ============================================================================

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
LOCK_FILE="/tmp/${SCRIPT_NAME}.lock"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# Default configuration
CPU_THRESHOLD=80
MEM_THRESHOLD=85
DISK_THRESHOLD=90
SERVICES=("nginx" "docker" "mysql")
AUTO_RESTART_FAILED_SERVICES=true
RESTART_ATTEMPTS=2
RESTART_DELAY=3
LOG_DIR="/var/log/server-stats"
LOG_FILE="${LOG_DIR}/server-stats.log"
LOG_ROTATION_SIZE=$((10 * 1024 * 1024))
OUTPUT_JSON=false
OUTPUT_FILE=""
VERBOSE=false
ENABLE_ALERTS=false
WEBHOOK_URL=""
EMAIL_RECIPIENT=""

# Load configuration file if exists
CONFIG_FILE="${SCRIPT_DIR}/server-stats.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# ============================================================================
# COLORS & FORMATTING
# ============================================================================

RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
MAGENTA="\e[35m"
RESET="\e[0m"
BOLD="\e[1m"

# ============================================================================
# LOGGING & OUTPUT FUNCTIONS
# ============================================================================

# Initialize logging
init_logging() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR" 2>/dev/null || {
            LOG_DIR="/tmp"
            LOG_FILE="${LOG_DIR}/server-stats.log"
        }
    fi
}

# Rotate log file if too large
rotate_log() {
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt $LOG_ROTATION_SIZE ]; then
        mv "$LOG_FILE" "${LOG_FILE}.$(date +%s)"
        gzip "${LOG_FILE}".* 2>/dev/null || true
    fi
}

log() {
    local message="$1"
    echo -e "$message"
    echo -e "[${TIMESTAMP}] $message" >> "$LOG_FILE" 2>/dev/null || true
}

debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${MAGENTA}[DEBUG] $1${RESET}" | tee -a "$LOG_FILE" 2>/dev/null || true
    fi
}

info() {
    log "${BLUE}[INFO]${RESET} $1"
}

warn() {
    log "${YELLOW}[WARN]${RESET} $1"
}

alert() {
    log "${RED}[ALERT]${RESET} $1"
}

ok() {
    log "${GREEN}[OK]${RESET} $1"
}

success() {
    log "${GREEN}[SUCCESS]${RESET} $1"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Acquire lock file
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            alert "Another instance is running (PID: $pid)"
            exit 1
        else
            debug "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
    debug "Lock acquired (PID: $$)"
}

# Release lock file
release_lock() {
    rm -f "$LOCK_FILE"
    debug "Lock released"
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    release_lock
    [ $exit_code -ne 0 ] && alert "Script exited with code: $exit_code"
    exit $exit_code
}

# Trap signals
trap cleanup EXIT INT TERM

# Safe command execution with error handling
safe_exec() {
    local cmd="$1"
    debug "Executing: $cmd"
    if output=$(eval "$cmd" 2>&1); then
        echo "$output"
        return 0
    else
        warn "Command failed: $cmd"
        return 1
    fi
}

# Check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# JSON escaping
json_escape() {
    printf '%s\n' "$1" | sed -e 's/[\"]/\\&/g'
}

# ============================================================================
# ALERT SYSTEM
# ============================================================================

send_alert() {
    local title="$1"
    local message="$2"
    local severity="${3:-warning}"

    [ "$ENABLE_ALERTS" != true ] && return 0

    # Send webhook alert
    if [ -n "$WEBHOOK_URL" ]; then
        send_webhook_alert "$title" "$message" "$severity"
    fi

    # Send email alert
    if [ -n "$EMAIL_RECIPIENT" ] && command_exists mail; then
        send_email_alert "$title" "$message" "$severity"
    fi
}

send_webhook_alert() {
    local title="$1"
    local message="$2"
    local severity="$3"

    local payload=$(cat <<EOF
{
  "title": "$(json_escape "$title")",
  "text": "$(json_escape "$message")",
  "severity": "$severity",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "hostname": "$(hostname)"
}
EOF
)

    if command_exists curl; then
        curl -X POST -H 'Content-type: application/json' \
            --data "$payload" \
            "$WEBHOOK_URL" \
            >/dev/null 2>&1 || debug "Webhook send failed"
    fi
}

send_email_alert() {
    local title="$1"
    local message="$2"
    local severity="$3"

    local subject="[${severity^^}] Server Alert: $title"
    local body="Timestamp: $(date)
Server: $(hostname)
Severity: $severity

$message

---
Server Stats Monitor v$SCRIPT_VERSION
$(hostname -I)"

    echo "$body" | mail -s "$subject" "$EMAIL_RECIPIENT" 2>/dev/null || \
        debug "Email send failed"
}

# ============================================================================
# METRICS COLLECTION
# ============================================================================

# System Information
system_info() {
    info "${BOLD}System Information${RESET}"

    local os_name=""
    if [ -f /etc/os-release ]; then
        os_name=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
    else
        os_name=$(uname -s)
    fi

    echo "  OS: $os_name"
    echo "  Kernel: $(uname -r)"
    echo "  Hostname: $(hostname)"
    echo "  Uptime: $(uptime -p 2>/dev/null || uptime | awk -F'up' '{print $2}')"

    if command_exists hostnamectl; then
        echo "  Machine Type: $(hostnamectl --short)"
    fi
}

# CPU Information
cpu_info() {
    info "${BOLD}CPU Information${RESET}"

    if ! command_exists top; then
        warn "top command not found, skipping CPU metrics"
        return
    fi

    local cpu_idle cpu_usage cores load

    # More reliable CPU calculation
    cpu_idle=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $8}' | sed 's/%id,//')
    if [ -z "$cpu_idle" ]; then
        cpu_idle=$(top -bn1 2>/dev/null | awk '/Cpu/ {print $8}' | head -1)
    fi

    cpu_usage=$(awk "BEGIN {printf \"%.2f\", 100 - ${cpu_idle:-0}}")
    cores=$(nproc 2>/dev/null || echo "1")
    load=$(uptime | awk -F'load average:' '{print $2}' | xargs)

    echo "  Cores: $cores"
    echo "  Current Usage: ${cpu_usage}%"
    echo "  Load Average: $load"

    if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
        alert "High CPU usage detected: ${cpu_usage}%"
        send_alert "High CPU Usage" "Current CPU usage: ${cpu_usage}% (threshold: ${CPU_THRESHOLD}%)" "critical"
    else
        ok "CPU usage normal (${cpu_usage}%)"
    fi
}

# Memory Information
memory_info() {
    info "${BOLD}Memory Information${RESET}"

    local total used free percent

    read total used free <<< $(free -m 2>/dev/null | awk '/Mem:/ {print $2, $3, $4}')

    if [ -z "$total" ]; then
        warn "Unable to retrieve memory information"
        return
    fi

    percent=$(awk "BEGIN {printf \"%.2f\", $used/$total*100}")

    echo "  Total: ${total}MB"
    echo "  Used: ${used}MB"
    echo "  Free: ${free}MB"
    echo "  Usage: ${percent}%"

    if (( $(echo "$percent > $MEM_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
        alert "High Memory usage: ${percent}%"
        send_alert "High Memory Usage" "Memory usage: ${percent}% (threshold: ${MEM_THRESHOLD}%)" "warning"
    else
        ok "Memory usage normal (${percent}%)"
    fi
}

# Disk Information
disk_info() {
    info "${BOLD}Disk Information${RESET}"

    if ! command_exists df; then
        warn "df command not found, skipping disk metrics"
        return
    fi

    df -h 2>/dev/null | grep -v tmpfs | grep -v udev | grep -v "^Filesystem" | {
        local any_high=false
        while read -r line; do
            local usage mount
            usage=$(echo "$line" | awk '{print $5}' | sed 's/%//')
            mount=$(echo "$line" | awk '{print $6}')

            # Validate usage is a number
            if [[ "$usage" =~ ^[0-9]+$ ]]; then
                if [ "$usage" -gt "$DISK_THRESHOLD" ]; then
                    alert "High disk usage on $mount: ${usage}%"
                    send_alert "High Disk Usage" "Disk usage on $mount: ${usage}% (threshold: ${DISK_THRESHOLD}%)" "warning"
                    any_high=true
                fi
                echo "  $mount: ${usage}% ($(echo $line | awk '{print $3}'))"
            fi
        done

        [ "$any_high" != true ] && ok "All disks normal"
    }
}

# Network Information
network_info() {
    info "${BOLD}Network Information${RESET}"

    if command_exists ss; then
        local connections=$(ss -s 2>/dev/null | grep TCP | awk '{print $3}' | head -1)
        echo "  Active TCP Connections: ${connections:-N/A}"

        echo "  Listening Ports:"
        ss -tulpn 2>/dev/null | tail -n +2 | head -5 | while read -r line; do
            echo "    $(echo $line | awk '{print $4, $7}')"
        done
    else
        warn "ss command not found, skipping network metrics"
    fi
}

# Service Status
service_check() {
    info "${BOLD}Service Status${RESET}"

    if ! command_exists systemctl; then
        warn "systemctl not available, skipping service checks"
        return
    fi

    for svc in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            ok "$svc is ${GREEN}running${RESET}"
        else
            alert "$svc is ${RED}NOT running${RESET}"
            send_alert "Service Down" "Service $svc is not running" "critical"
        fi
    done
}

# Auto-Restart Failed Services
restart_service() {
    local svc="$1"

    if ! systemctl list-unit-files 2>/dev/null | awk '{print $1}' | grep -qx "${svc}.service"; then
        warn "Service unit ${svc}.service not found"
        return 1
    fi

    alert "Attempting to restart $svc..."

    for ((attempt=1; attempt<=RESTART_ATTEMPTS; attempt++)); do
        if systemctl restart "$svc" 2>/dev/null; then
            sleep "$RESTART_DELAY"

            if systemctl is-active --quiet "$svc" 2>/dev/null; then
                ok "$svc restarted successfully (attempt $attempt)"
                send_alert "Service Recovered" "Service $svc has been restarted and is running" "info"
                return 0
            fi
        fi

        warn "$svc restart attempt $attempt failed"
        [ $attempt -lt $RESTART_ATTEMPTS ] && sleep "$RESTART_DELAY"
    done

    alert "Failed to restart $svc after $RESTART_ATTEMPTS attempts"
    send_alert "Service Restart Failed" "Failed to restart $svc after $RESTART_ATTEMPTS attempts" "critical"
    return 1
}

auto_restart_failed_services() {
    if [ "$AUTO_RESTART_FAILED_SERVICES" != true ]; then
        return
    fi

    info "${BOLD}Service Auto-Restart${RESET}"

    for svc in "${SERVICES[@]}"; do
        if ! systemctl is-active --quiet "$svc" 2>/dev/null; then
            warn "$svc is down, attempting restart..."
            restart_service "$svc"
        fi
    done
}

# Security Information
security_check() {
    info "${BOLD}Security Information${RESET}"

    # Failed login attempts
    if [ -f /var/log/auth.log ]; then
        local fails=$(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l)
        echo "  Failed Login Attempts: $fails"

        if [ "$fails" -gt 10 ]; then
            warn "Multiple failed login attempts detected"
            send_alert "Security Alert" "Multiple failed login attempts detected ($fails total)" "warning"
        fi
    fi

    # Open ports
    if command_exists ss; then
        echo "  Listening Ports:"
        ss -tulpn 2>/dev/null | tail -n +2 | while read -r line; do
            echo "    $(echo $line | awk '{print $4}')"
        done | head -5
    fi
}

# Top Processes
top_processes() {
    info "${BOLD}Top Processes${RESET}"

    if ! command_exists ps; then
        warn "ps command not found"
        return
    fi

    echo "  Top CPU Consumers:"
    ps -eo pid,cmd,%cpu --sort=-%cpu 2>/dev/null | tail -n +2 | head -4 | \
        awk '{printf "    PID %s: %.1f%% - %s\n", $1, $3, substr($0, index($0,$2))}'

    echo "  Top Memory Consumers:"
    ps -eo pid,cmd,%mem --sort=-%mem 2>/dev/null | tail -n +2 | head -4 | \
        awk '{printf "    PID %s: %.1f%% - %s\n", $1, $3, substr($0, index($0,$2))}'
}

# ============================================================================
# JSON OUTPUT
# ============================================================================

generate_json_report() {
    local cpu_idle cpu_usage cores load
    local total_mem used_mem free_mem mem_percent
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Collect metrics
    cpu_idle=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $8}' | sed 's/%id,//' || echo "0")
    cpu_usage=$(awk "BEGIN {printf \"%.2f\", 100 - ${cpu_idle:-0}}")
    cores=$(nproc 2>/dev/null || echo "1")
    load=$(uptime | awk -F'load average:' '{print $2}' | xargs)

    read total_mem used_mem free_mem <<< $(free -m 2>/dev/null | awk '/Mem:/ {print $2, $3, $4}')
    mem_percent=$(awk "BEGIN {printf \"%.2f\", $used_mem/$total_mem*100}")

    cat <<EOF
{
  "version": "$SCRIPT_VERSION",
  "timestamp": "$timestamp",
  "hostname": "$(hostname)",
  "system": {
    "os": "$([ -f /etc/os-release ] && grep PRETTY_NAME /etc/os-release | cut -d'"' -f2 || uname -s)",
    "kernel": "$(uname -r)",
    "uptime": "$(uptime -p 2>/dev/null || echo 'N/A')"
  },
  "cpu": {
    "cores": $cores,
    "usage_percent": $cpu_usage,
    "load_average": "$load",
    "threshold": $CPU_THRESHOLD
  },
  "memory": {
    "total_mb": $total_mem,
    "used_mb": $used_mem,
    "free_mb": $free_mem,
    "usage_percent": $mem_percent,
    "threshold": $MEM_THRESHOLD
  },
  "services": [
    $(for svc in "${SERVICES[@]}"; do
        local status=$(systemctl is-active "$svc" 2>/dev/null && echo "running" || echo "stopped")
        echo "    {\"name\": \"$svc\", \"status\": \"$status\"}"
    done | paste -sd ',' - || echo "")
  ]
}
EOF
}

# ============================================================================
# COMMAND-LINE ARGUMENT PARSING
# ============================================================================

show_help() {
    cat <<EOF
${BOLD}Server Stats Monitor v${SCRIPT_VERSION}${RESET}
Production-grade server performance monitoring tool

${BOLD}USAGE:${RESET}
    $SCRIPT_NAME [OPTIONS]

${BOLD}OPTIONS:${RESET}
    -h, --help              Show this help message
    -v, --version           Show version information
    -j, --json              Output metrics as JSON
    -o, --output FILE       Save output to file
    -s, --services SRVCS    Monitor specific services (comma-separated)
    -c, --cpu THRESHOLD     CPU usage threshold (default: 80%)
    -m, --memory THRESHOLD  Memory usage threshold (default: 85%)
    -d, --disk THRESHOLD    Disk usage threshold (default: 90%)
    -a, --alerts            Enable alert notifications
    -V, --verbose           Enable verbose/debug output

${BOLD}EXAMPLES:${RESET}
    # Basic monitoring
    $SCRIPT_NAME

    # JSON output with custom thresholds
    $SCRIPT_NAME --json -o report.json -c 75 -m 80

    # Monitor specific services
    $SCRIPT_NAME --services nginx,postgres,redis

    # Enable verbose output
    $SCRIPT_NAME --verbose

${BOLD}CONFIGURATION:${RESET}
    Edit ${CONFIG_FILE} to customize default settings

${BOLD}LOGGING:${RESET}
    Logs are stored in: $LOG_DIR/

${BOLD}For more information:${RESET}
    https://github.com/shuvo-halder/performance-stats

EOF
}

show_version() {
    echo "Server Stats Monitor v$SCRIPT_VERSION"
    echo "License: MIT"
    echo "Repository: https://github.com/shuvo-halder/performance-stats"
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                show_version
                exit 0
                ;;
            -j|--json)
                OUTPUT_JSON=true
                shift
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -s|--services)
                IFS=',' read -r -a SERVICES <<< "$2"
                shift 2
                ;;
            -c|--cpu)
                CPU_THRESHOLD="$2"
                shift 2
                ;;
            -m|--memory)
                MEM_THRESHOLD="$2"
                shift 2
                ;;
            -d|--disk)
                DISK_THRESHOLD="$2"
                shift 2
                ;;
            -a|--alerts)
                ENABLE_ALERTS=true
                shift
                ;;
            -V|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                warn "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    # Initialize
    acquire_lock
    init_logging
    rotate_log

    parse_arguments "$@"

    # Output header
    local header="╔════════════════════════════════════════════════════════════════╗
║           SERVER PERFORMANCE MONITOR v${SCRIPT_VERSION}           ║
║                 $(date '+%Y-%m-%d %H:%M:%S')                       ║
╚════════════════════════════════════════════════════════════════╝"

    if [ "$OUTPUT_JSON" = true ]; then
        generate_json_report | tee "${OUTPUT_FILE:-.}"
    else
        echo -e "$header"
        echo ""

        system_info
        echo ""
        cpu_info
        echo ""
        memory_info
        echo ""
        disk_info
        echo ""
        network_info
        echo ""
        service_check
        echo ""
        auto_restart_failed_services
        echo ""
        security_check
        echo ""
        top_processes
        echo ""

        echo "╚════════════════════════════════════════════════════════════════╝"

        # Save to file if specified
        if [ -n "$OUTPUT_FILE" ] && [ "$OUTPUT_FILE" != "/dev/stdout" ]; then
            {
                echo "$header"
                echo ""
                system_info
                echo ""
                cpu_info
                echo ""
                memory_info
                echo ""
                disk_info
                echo ""
                network_info
                echo ""
                service_check
                echo ""
                auto_restart_failed_services
                echo ""
                security_check
                echo ""
                top_processes
                echo ""
                echo "╚════════════════════════════════════════════════════════════════╝"
            } > "$OUTPUT_FILE"

            ok "Report saved to: $OUTPUT_FILE"
        fi
    fi

    ok "Monitoring complete"
}

# Run main function
main "$@"
