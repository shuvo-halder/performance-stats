"""
Deep Network Insight Collector.

Provides:
  - Active connections per state (ESTABLISHED, TIME_WAIT, CLOSE_WAIT, etc.)
  - Top connected IPs (network-level, not HTTP)
  - Connections per port
  - Connection rate (new connections/sec)
  - Packet drops/errors
"""

import asyncio
import logging
import re
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("server-stats.metrics.network")

# Regex to parse ss -tun output lines
# Example: ESTAB 0 0 192.168.1.1:5432 10.0.0.1:45123
SS_LINE_PATTERN = re.compile(
    r'^(?P<state>\w+)\s+\d+\s+\d+\s+'
    r'(?P<local>[^\s]+)\s+'
    r'(?P<remote>[^\s]+)'
)


class DeepNetworkCollector:
    """
    Collects deep network metrics using ss and /proc/net/.
    Runs as a background task every 2 seconds.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        # Connection counts per state
        self._conn_states: Dict[str, int] = {}
        # Top IPs (count per remote IP)
        self._top_ips: Dict[str, int] = {}
        # Connections per port
        self._port_counts: Dict[int, int] = {}
        # Total connections
        self._total_connections = 0
        # Connection rate tracking
        self._conn_rate_buffer: deque = deque(maxlen=30)  # last 30 samples
        self._last_total = 0
        self._last_sample_time = 0.0
        self._conn_rate = 0.0

    async def collect(self):
        """Run ss -tun and parse output."""
        try:
            output = await self._run_ss()
            if not output:
                return

            states = defaultdict(int)
            ips = defaultdict(int)
            ports = defaultdict(int)
            total = 0

            lines = output.strip().split("\n")
            for line in lines:
                if "State" in line or "Recv-Q" in line:
                    continue
                match = SS_LINE_PATTERN.match(line.strip())
                if not match:
                    continue

                state = match.group("state")
                remote = match.group("remote")
                local = match.group("local")

                states[state] += 1
                total += 1

                # Extract remote IP (strip port)
                if "[" in remote:
                    # IPv6: [addr]:port
                    remote_ip = remote.split("]:")[0].lstrip("[")
                else:
                    remote_ip = remote.rsplit(":", 1)[0] if ":" in remote else remote

                if remote_ip and remote_ip != "::":
                    ips[remote_ip] += 1

                # Extract local port
                if "[" in local:
                    local_port = local.split("]:")[-1]
                else:
                    local_port = local.rsplit(":", 1)[-1] if ":" in local else "0"
                try:
                    ports[int(local_port)] += 1
                except ValueError:
                    pass

            async with self._lock:
                self._conn_states = dict(states)
                self._top_ips = dict(sorted(ips.items(), key=lambda x: -x[1])[:20])
                self._port_counts = dict(sorted(ports.items(), key=lambda x: -x[1])[:15])
                self._total_connections = total

                # Calculate connection rate
                now = asyncio.get_event_loop().time()
                if self._last_sample_time > 0:
                    dt = now - self._last_sample_time
                    if dt > 0:
                        delta = total - self._last_total
                        rate = max(0, delta / dt)
                        self._conn_rate_buffer.append(rate)
                        # Smooth the rate
                        self._conn_rate = sum(self._conn_rate_buffer) / len(self._conn_rate_buffer)
                self._last_total = total
                self._last_sample_time = now

        except Exception as e:
            logger.error(f"Deep network collect error: {e}")

    async def _run_ss(self) -> Optional[str]:
        """Run ss -tun and return output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ss", "-tun",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode().strip() if stdout else None
        except FileNotFoundError:
            logger.warning("ss command not available on this system")
            return None
        except Exception as e:
            logger.error(f"Error running ss: {e}")
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

    async def get_history(self) -> dict:
        """Get connection rate history."""
        async with self._lock:
            states_history = dict(self._conn_states)
            return {
                "connection_states": states_history,
                "connection_rate": round(self._conn_rate, 2),
            }


# ── Global singleton ────────────────────────────────────────────────────
deep_network = DeepNetworkCollector()