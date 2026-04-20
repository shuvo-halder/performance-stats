#!/bin/bash

set -euo pipefail

# ================= CONFIG =================
CPU_THRESHOLD=80
MEM_THRESHOLD=85
DISK_THRESHOLD=90

SERVICES=("nginx" "docker" "mysql")

OUTPUT_JSON=false
OUTPUT_FILE=""

# =============== COLORS ===================
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
RESET="\e[0m"

# =============== UTILS ====================
log() {
    echo -e "$1"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${RESET}"
}

alert() {
    echo -e "${RED}[ALERT] $1${RESET}"
}

ok() {
    echo -e "${GREEN}[OK] $1${RESET}"
}

# ============ SYSTEM INFO =================
system_info() {
    log "\n${BLUE}--- System Info ---${RESET}"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "OS: $PRETTY_NAME"
    else
        uname -a
    fi

    echo "Kernel: $(uname -r)"
    echo "Uptime: $(uptime -p)"
}

# ============ CPU INFO ====================
cpu_info() {
    log "\n${BLUE}--- CPU Info ---${RESET}"

    cpu_idle=$(top -bn1 | awk '/Cpu/ {print $8}')
    cpu_usage=$(awk "BEGIN {print 100 - $cpu_idle}")

    cores=$(nproc)
    load=$(uptime | awk -F'load average:' '{ print $2 }')

    echo "Cores: $cores"
    echo "Load Avg:$load"
    echo "CPU Usage: ${cpu_usage}%"

    if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l) )); then
        alert "High CPU usage: $cpu_usage%"
    else
        ok "CPU usage normal"
    fi
}

# ============ MEMORY ======================
memory_info() {
    log "\n${BLUE}--- Memory Info ---${RESET}"

    read total used free <<< $(free -m | awk '/Mem:/ {print $2, $3, $4}')
    percent=$(awk "BEGIN {printf \"%.2f\", $used/$total*100}")

    echo "Used: ${used}MB / ${total}MB (${percent}%)"

    if (( $(echo "$percent > $MEM_THRESHOLD" | bc -l) )); then
        alert "High Memory usage: $percent%"
    else
        ok "Memory usage normal"
    fi
}

# ============ DISK ========================
disk_info() {
    log "\n${BLUE}--- Disk Info ---${RESET}"

    df -h | grep -v tmpfs | grep -v udev

    while read line; do
        usage=$(echo $line | awk '{print $5}' | sed 's/%//')
        mount=$(echo $line | awk '{print $6}')

        if [ "$usage" -gt "$DISK_THRESHOLD" ]; then
            alert "Disk high usage on $mount: ${usage}%"
        fi
    done < <(df -h | tail -n +2)
}

# ============ NETWORK =====================
network_info() {
    log "\n${BLUE}--- Network Info ---${RESET}"

    echo "Active Connections:"
    ss -s

    echo -e "\nListening Ports:"
    ss -tulpn | head -n 10
}

# ============ SERVICES ====================
service_check() {
    log "\n${BLUE}--- Service Status ---${RESET}"

    for svc in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$svc"; then
            ok "$svc is running"
        else
            alert "$svc is NOT running"
        fi
    done
}

# ============ SECURITY ====================
security_check() {
    log "\n${BLUE}--- Security Check ---${RESET}"

    if [ -f /var/log/auth.log ]; then
        fails=$(grep "Failed password" /var/log/auth.log | wc -l)
        echo "Failed logins: $fails"
    fi

    echo "Open Ports:"
    ss -tulpn | head -n 10
}

# ============ TOP PROCESS =================
top_processes() {
    log "\n${BLUE}--- Top Processes ---${RESET}"

    echo "Top CPU:"
    ps -eo pid,cmd,%cpu --sort=-%cpu | head -n 6

    echo -e "\nTop Memory:"
    ps -eo pid,cmd,%mem --sort=-%mem | head -n 6
}

# ============ ARG PARSER ==================
while getopts "jo:s:" opt; do
  case $opt in
    j) OUTPUT_JSON=true ;;
    o) OUTPUT_FILE="$OPTARG" ;;
    s) IFS=',' read -r -a SERVICES <<< "$OPTARG" ;;
  esac
done

# ============ MAIN ========================
main() {
    echo "======================================="
    echo "     ADVANCED SERVER MONITOR REPORT    "
    echo "======================================="

    system_info
    cpu_info
    memory_info
    disk_info
    network_info
    service_check
    security_check
    top_processes

    echo "======================================="
    echo "               END REPORT              "
    echo "======================================="
}

main | tee "${OUTPUT_FILE:-/dev/stdout}"
