"""
Deep Network Insight Collector.

Cross-platform support:
  - Linux: uses `ss -tun` for detailed connection states
  - All platforms: graceful fallback to empty data on failure

Provides:
  - Active connections per state (ESTABLISHED, TIME_WAIT, CLOSE_WAIT, etc.)
  - Top connected IPs (network-level)
  - Connections per port
  - Connection rate (new connections/sec)
"""

import asyncio
import logging
import platform
import re
from collections import defaultdict, deque
from typing import Dict, List, Optional

logger = logging.getLogger("server-stats.metrics.network")

# Regex to parse ss -tun output (Linux only)
SS_LINE_PATTERN = re.compile(
    r'^(?P<state>\w+)\s+'
    r'\d+\s+\d+\s+'
    r'(?P<local>[^\s]+)\s+'
    r'(?P<remote>[^\s]+)'
)

# Map psutil connection status to our state names
PSUTIL_STATUS_MAP = {
    "ESTABLISHED": "ESTABLISHED",
    "SYN_SENT": "SYN_SENT",
    "SYN_RECV": "SYN_RECV",
    "FIN_WAIT1": "FIN_WAIT",
    "FIN_WAIT2": "FIN_WAIT",
    "TIME_WAIT": "TIME_WAIT",
    "CLOSE": "CLOSE",
    "CLOSE_WAIT": "CLOSE_WAIT",
    "LAST_ACK": "LAST_ACK",
    "LISTEN": "LISTEN",
    "CLOSING": "CLOSING",
    "NONE": "NONE",
}


class DeepNetworkCollector:
    """
    Collects deep network metrics.
    Linux: uses `ss -tun` for live parsing
    Fallback: uses `psutil.net_connections()`
    Gracefully returns empty data on any failure.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._conn_states: Dict[str, int] = {}
        self._top_ips: Dict[str, int] = {}
        self._port_counts: Dict[int, int] = {}
        self._total_connections = 0
        self._conn_rate_buffer: deque = deque(maxlen=30)
        self._last_total = 0
        self._last_sample_time = 0.0
        self._conn_rate = 0.0
        self._is_linux = platform.system() == "Linux"
        self._has_ss = None  # Lazily check if ss is available

    async def check_ss_available(self) -> bool:
        """Check if ss command is available and has output."""
        if self._has_ss is not None:
            return self._has_ss
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", "ss",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            self._has_ss = bool(stdout and stdout.decode().strip())
            return self._has_ss
        except Exception:
            self._has_ss = False
            return False

    async def collect(self):
        """Collect network metrics. Returns silently on failure."""
        try:
            if self._is_linux and await self.check_ss_available():
                await self._collect_linux()
            else:
                await self._collect_psutil()
        except Exception as e:
            logger.warning(f"Network collect failed (returning empty): {e}")
            # Ensure we always have valid state
            await self._reset_state()

    async def _reset_state(self):
        """Reset to safe empty state."""
        async with self._lock:
            if not self._conn_states:
                self._conn_states = {}
            if not self._top_ips:
                self._top_ips = {}
            if not self._port_counts:
                self._port_counts = {}

    async def _collect_linux(self):
        """Linux: parse ss -tun output."""
        output = await self._run_ss()
        if not output:
            # Try psutil fallback
            await self._collect_psutil()
            return

        states = defaultdict(int)
        ips = defaultdict(int)
        ports = defaultdict(int)
        total = 0

        for line in output.strip().split("\n"):
            if "State" in line or "Recv-Q" in line or "Netid" in line:
                continue
            match = SS_LINE_PATTERN.match(line.strip())
            if not match:
                continue

            state = match.group("state")
            remote = match.group("remote")
            local = match.group("local")

            states[state] += 1
            total += 1

            # Remote IP
            if "[" in remote:
                remote_ip = remote.split("]:")[0].lstrip("[")
            else:
                remote_ip = remote.rsplit(":", 1)[0] if ":" in remote else remote
            if remote_ip and remote_ip != "::" and remote_ip != "0.0.0.0":
                ips[remote_ip] += 1

            # Local port
            if "[" in local:
                local_port = local.split("]:")[-1]
            else:
                local_port = local.rsplit(":", 1)[-1] if ":" in local else "0"
            try:
                ports[int(local_port)] += 1
            except ValueError:
                pass

        if total > 0:
            await self._update_state(dict(states), dict(ips), dict(ports), total)
        else:
            await self._reset_state()

    async def _collect_psutil(self):
        """Cross-platform: use psutil.net_connections()."""
        try:
            import psutil
            conns = psutil.net_connections(kind='inet')
        except ImportError:
            logger.debug("psutil not available for network connections")
            await self._reset_state()
            return
        except (psutil.AccessDenied, PermissionError):
            logger.debug("psutil.net_connections() requires root")
            await self._reset_state()
            return
        except Exception as e:
            logger.debug(f"net_connections() failed: {e}")
            await self._reset_state()
            return

        states = defaultdict(int)
        ips = defaultdict(int)
        ports = defaultdict(int)
        total = 0

        for conn in conns:
            status = PSUTIL_STATUS_MAP.get(conn.status, conn.status)
            states[status] += 1
            total += 1

            if conn.raddr:
                remote_ip = conn.raddr.ip
                if remote_ip and remote_ip != "::" and remote_ip != "0.0.0.0" and remote_ip != "127.0.0.1":
                    ips[remote_ip] += 1

            if conn.laddr:
                ports[conn.laddr.port] = ports.get(conn.laddr.port, 0) + 1

        if total > 0:
            await self._update_state(dict(states), dict(ips), dict(ports), total)
        else:
            await self._reset_state()

    async def _update_state(self, states: dict, ips: dict, ports: dict, total: int):
        """Update internal state with collected data and compute rate."""
        async with self._lock:
            self._conn_states = states
            self._top_ips = dict(sorted(ips.items(), key=lambda x: -x[1])[:20])
            self._port_counts = dict(sorted(ports.items(), key=lambda x: -x[1])[:15])
            self._total_connections = total

            now = asyncio.get_event_loop().time()
            if self._last_sample_time > 0:
                dt = now - self._last_sample_time
                if dt > 0:
                    delta = total - self._last_total
                    rate = max(0, delta / dt)
                    self._conn_rate_buffer.append(rate)
                    self._conn_rate = sum(self._conn_rate_buffer) / len(self._conn_rate_buffer) if self._conn_rate_buffer else 0
            self._last_total = total
            self._last_sample_time = now

    async def _run_ss(self) -> Optional[str]:
        """Run ss -tun and return output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ss", "-tun",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                if proc.returncode != 0:
                    logger.debug(f"ss returned {proc.returncode}: {stderr.decode()[:200]}")
                    return None
                return stdout.decode().strip() if stdout else None
            except asyncio.TimeoutError:
                proc.kill()
                logger.debug("ss command timed out")
                return None
        except FileNotFoundError:
            logger.debug("ss command not available")
            return None
        except Exception as e:
            logger.debug(f"Error running ss: {e}")
            return None

    async def get_snapshot(self) -> dict:
        """Get current deep network snapshot."""
        async with self._lock:
            return {
                "total_connections": self._total_connections,
                "connection_states": dict(self._conn_states),
                "top_ips": [{"ip": ip, "count": cnt} for ip, cnt in
                           sorted(self._top_ips.items(), key=lambda x: -x[1])[:10]],
                "port_counts": [{"port": p, "count": c} for p, c in
                               sorted(self._port_counts.items(), key=lambda x: -x[1])[:10]],
                "connection_rate": round(self._conn_rate, 2),
            }


# ── Global singleton ────────────────────────────────────────────────────
deep_network = DeepNetworkCollector()