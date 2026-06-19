#!/bin/bash
<<<<<<< HEAD
set -euo pipefail

AGENT_VERSION="1.0.0"
INSTALL_DIR="/usr/local/lib/server-stats-agent"
BIN_DIR="/usr/local/bin"
CONFIG_DIR="/etc"
LOG_DIR="/var/log"
PID_DIR="/var/run"
AGENT_BIN="${BIN_DIR}/server-stats-agent"
AGENT_SCRIPT="${INSTALL_DIR}/monitor_agent.py"
AGENT_CONFIG="${CONFIG_DIR}/server-stats-agent.conf"
AGENT_LOG="${LOG_DIR}/server-stats-agent.log"
SERVICE_FILE="/etc/systemd/system/server-stats-agent.service"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
=======
# ============================================================================
# Server Stats Monitoring Agent - One-line Installation Script
# ============================================================================
# Usage:
#   curl -sSL https://your-server.com/install.sh | bash
#   curl -sSL https://your-server.com/install.sh | bash -s -- --server https://api.example.com --token YOUR_TOKEN
# ============================================================================

set -euo pipefail

AGENT_VERSION="1.0.0"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc"
LOG_DIR="/var/log"
PID_DIR="/var/run"
AGENT_BIN="${INSTALL_DIR}/server-stats-agent"
AGENT_CONFIG="${CONFIG_DIR}/server-stats-agent.conf"
AGENT_LOG="${LOG_DIR}/server-stats-agent.log"
AGENT_PID="${PID_DIR}/server-stats-agent.pid"
SERVICE_FILE="/etc/systemd/system/server-stats-agent.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
>>>>>>> aea3279 (update :: v3 Tier-1)

echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Server Stats Agent v${AGENT_VERSION} Installer     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

<<<<<<< HEAD
if [[ $EUID -ne 0 ]]; then echo -e "${RED}Error: Must be run as root${NC}"; exit 1; fi

SERVER_URL=""; AGENT_TOKEN=""; COLLECT_INTERVAL=60
=======
# Check root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Parse arguments
SERVER_URL=""
AGENT_TOKEN=""
COLLECT_INTERVAL=60

>>>>>>> aea3279 (update :: v3 Tier-1)
while [[ $# -gt 0 ]]; do
    case "$1" in
        --server) SERVER_URL="$2"; shift 2 ;;
        --token) AGENT_TOKEN="$2"; shift 2 ;;
        --interval) COLLECT_INTERVAL="$2"; shift 2 ;;
<<<<<<< HEAD
        --help) echo "Usage: curl -sSL https://your-server.com/install.sh | bash -s -- --server URL --token TOKEN"; exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

if [[ -z "$SERVER_URL" || -z "$AGENT_TOKEN" ]]; then
    echo -e "${RED}Error: --server and --token are required${NC}"
    exit 1
fi

# ── Step 1: Install Dependencies ─────────────────────────────────────
echo -e "${YELLOW}[1/5] Installing Python dependencies...${NC}"

# Detect OS and use package manager + pip with --break-system-packages
install_pkg() {
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq python3-pip python3-psutil python3-requests 2>/dev/null && return 0
        # Fallback: pip with --break-system-packages
        pip3 install psutil requests --break-system-packages --quiet 2>/dev/null && return 0
        pip3 install psutil requests --quiet 2>/dev/null && return 0
    elif command -v yum &>/dev/null; then
        yum install -y python3-pip python3-psutil python3-requests 2>/dev/null && return 0
        pip3 install psutil requests --quiet 2>/dev/null && return 0
    elif command -v dnf &>/dev/null; then
        dnf install -y python3-pip python3-psutil python3-requests 2>/dev/null && return 0
        pip3 install psutil requests --quiet 2>/dev/null && return 0
    else
        pip3 install psutil requests --break-system-packages --quiet 2>/dev/null && return 0
        pip3 install psutil requests --quiet 2>/dev/null && return 0
    fi
    return 1
}

if ! install_pkg; then
    echo -e "${RED}Error: Could not install Python dependencies${NC}"
    echo "Try manually: apt-get install -y python3-pip python3-psutil python3-requests"
=======
        --help)
            echo "Usage: curl -sSL https://your-server.com/install.sh | bash -s -- [options]"
            echo ""
            echo "Options:"
            echo "  --server URL     Central API server URL (required)"
            echo "  --token TOKEN    Agent authentication token (required)"
            echo "  --interval SEC   Collection interval in seconds (default: 60)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Install Python dependencies ──────────────────────────────────────
echo -e "${YELLOW}[1/5] Installing Python dependencies...${NC}"
if command -v pip3 &>/dev/null; then
    pip3 install psutil requests --quiet 2>/dev/null || pip3 install psutil requests
elif command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-pip python3-psutil python3-requests 2>/dev/null
elif command -v yum &>/dev/null; then
    yum install -y python3-pip python3-psutil python3-requests 2>/dev/null
else
    echo -e "${RED}Error: Could not install Python dependencies${NC}"
>>>>>>> aea3279 (update :: v3 Tier-1)
    exit 1
fi
echo -e "${GREEN}  ✔ Dependencies installed${NC}"

<<<<<<< HEAD
# ── Step 2: Deploy Agent Script ──────────────────────────────────────
echo -e "${YELLOW}[2/5] Deploying agent script...${NC}"

# Remove old installation if exists
rm -rf "${INSTALL_DIR}" "${AGENT_BIN}" 2>/dev/null || true

mkdir -p "${INSTALL_DIR}"

# Find the agent script (either local or download)
if [[ -f "monitor_agent.py" ]]; then
    cp monitor_agent.py "${AGENT_SCRIPT}"
elif [[ -n "${SERVER_URL}" ]]; then
    echo -e "${YELLOW}  Downloading from ${SERVER_URL}/api/agent/download...${NC}"
    curl -sSL "${SERVER_URL}/api/agent/download" -o "${AGENT_SCRIPT}" 2>/dev/null || true
fi

if [[ ! -f "${AGENT_SCRIPT}" ]]; then
    echo -e "${RED}Error: Agent script not available${NC}"
    echo "Download manually: curl -sSL https://raw.githubusercontent.com/shuvo-halder/performance-stats/main/backend/app/agent/monitor_agent.py -o monitor_agent.py"
=======
# ── Download agent script ────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Deploying agent script...${NC}"

# The agent script is embedded or downloaded from the central server
# For production, this would download from the API server
# For now, we expect the agent script to be copied manually or via a real download
AGENT_SOURCE="/tmp/server-stats-agent.py"

if [[ -f "monitor_agent.py" ]]; then
    cp monitor_agent.py "${AGENT_SOURCE}"
elif [[ -f "${INSTALL_DIR}/server-stats-agent.py" ]]; then
    cp "${INSTALL_DIR}/server-stats-agent.py" "${AGENT_SOURCE}"
else
    echo -e "${YELLOW}  ⚠ Agent script not found locally, attempting download from server...${NC}"
    if [[ -n "${SERVER_URL}" ]]; then
        curl -sSL "${SERVER_URL}/api/agent/download" -o "${AGENT_SOURCE}" 2>/dev/null || true
    fi
fi

if [[ ! -f "${AGENT_SOURCE}" ]]; then
    echo -e "${RED}Error: Agent script not available. Please provide monitor_agent.py${NC}"
    echo "Copy monitor_agent.py to this directory and re-run, or use:"
    echo "  curl -sSL https://your-server.com/api/agent/download -o monitor_agent.py"
>>>>>>> aea3279 (update :: v3 Tier-1)
    exit 1
fi

# Create wrapper script
cat > "${AGENT_BIN}" << 'WRAPPER'
#!/bin/bash
exec python3 /usr/local/lib/server-stats-agent/monitor_agent.py "$@"
WRAPPER

<<<<<<< HEAD
chmod +x "${AGENT_SCRIPT}" "${AGENT_BIN}"
echo -e "${GREEN}  ✔ Agent deployed to ${AGENT_BIN}${NC}"

# ── Step 3: Create Config ────────────────────────────────────────────
=======
mkdir -p "${INSTALL_DIR}/server-stats-agent"
cp "${AGENT_SOURCE}" "${INSTALL_DIR}/server-stats-agent/monitor_agent.py"
chmod +x "${AGENT_BIN}"
chmod +x "${INSTALL_DIR}/server-stats-agent/monitor_agent.py"
echo -e "${GREEN}  ✔ Agent deployed to ${AGENT_BIN}${NC}"

# ── Create configuration ─────────────────────────────────────────────
>>>>>>> aea3279 (update :: v3 Tier-1)
echo -e "${YELLOW}[3/5] Creating configuration...${NC}"
cat > "${AGENT_CONFIG}" << EOF
# Server Stats Agent Configuration
SERVER_URL=${SERVER_URL}
AGENT_TOKEN=${AGENT_TOKEN}
COLLECT_INTERVAL=${COLLECT_INTERVAL}
HEARTBEAT_INTERVAL=30
EOF
chmod 600 "${AGENT_CONFIG}"
<<<<<<< HEAD
echo -e "${GREEN}  ✔ Config created at ${AGENT_CONFIG}${NC}"

# ── Step 4: Create Systemd Service ───────────────────────────────────
=======
echo -e "${GREEN}  ✔ Configuration created at ${AGENT_CONFIG}${NC}"

# ── Create service file ──────────────────────────────────────────────
>>>>>>> aea3279 (update :: v3 Tier-1)
echo -e "${YELLOW}[4/5] Creating systemd service...${NC}"
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Server Stats Monitoring Agent
After=network.target

[Service]
Type=simple
ExecStart=${AGENT_BIN} --config ${AGENT_CONFIG}
Restart=always
RestartSec=10
StandardOutput=append:${AGENT_LOG}
StandardError=append:${AGENT_LOG}
<<<<<<< HEAD
=======
PIDFile=${AGENT_PID}
>>>>>>> aea3279 (update :: v3 Tier-1)
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload 2>/dev/null || true
echo -e "${GREEN}  ✔ Systemd service created${NC}"

<<<<<<< HEAD
# ── Step 5: Start Service ────────────────────────────────────────────
=======
# ── Start service ────────────────────────────────────────────────────
>>>>>>> aea3279 (update :: v3 Tier-1)
echo -e "${YELLOW}[5/5] Starting agent...${NC}"
systemctl enable server-stats-agent 2>/dev/null || true
systemctl start server-stats-agent 2>/dev/null || true

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation Complete! 🎉          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Binary:    ${AGENT_BIN}"
echo -e "  Config:    ${AGENT_CONFIG}"
echo -e "  Log:       ${AGENT_LOG}"
<<<<<<< HEAD
echo -e "  Service:   systemctl status server-stats-agent"
=======
echo -e "  Service:   ${SERVICE_FILE}"
echo ""
echo -e "  Commands:"
echo -e "    systemctl status server-stats-agent"
echo -e "    systemctl restart server-stats-agent"
echo -e "    journalctl -u server-stats-agent -f"
>>>>>>> aea3279 (update :: v3 Tier-1)
echo ""