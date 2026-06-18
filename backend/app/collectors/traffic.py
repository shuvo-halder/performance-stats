"""
Real-time traffic monitoring module.

Handles:
  - Async log tailing for nginx/apache access logs
  - Sliding-window aggregation (RPS, top IPs, top endpoints, status codes)
  - Network-level monitoring (active connections via ss, bandwidth via /proc/net/dev)
  - In-memory ring buffer for live WebSocket pushes
  - Batch DB flushing for history
  - Alert detection (RPS spikes, 5xx floods, single-IP DDoS)
"""

import asyncio
import re
import os
import time
import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.config import settings
from app.database import async_session, TrafficLog, TrafficAggregate

logger = logging.getLogger("server-stats.traffic")

# ── Regex patterns ──────────────────────────────────────────────────────
# Nginx combined log format:
#   $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
NGINX_PATTERN = re.compile(
    r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[[^\]]+\]\s+'
    r'"(?P<method>\S+)\s+(?P<endpoint>\S+)\s+\S+"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"'
)

# Apache combined format is the same as nginx combined
APACHE_PATTERN = NGINX_PATTERN

# ── In-memory state ─────────────────────────────────────────────────────

class TrafficState:
    """Thread-safe in-memory traffic state with sliding window."""

    def __init__(self, window_seconds: int = 60, batch_interval: int = 5):
        self.window = window_seconds
        self.batch_interval = batch_interval
        self._lock = asyncio.Lock()

        # Ring buffer of raw log entries (timestamp, ip, endpoint, status, size, ua, referer)
        self._entries: deque = deque(maxlen=100_000)

        # Network-level state
        self._active_connections = 0
        self._bandwidth_rx = 0   # bytes since last batch
        self._bandwidth_tx = 0

        # Last accumulated values for bandwidth delta calculation
        self._last_rx_bytes: Dict[str, int] = {}
        self._last_tx_bytes: Dict[str, int] = {}

        # Batch queue (entries queued for DB flush)
        self._batch_queue: List[tuple] = []

        # Alert counters (to avoid spamming same alerts)
        self._last_alerts: Dict[str, float] = {}

    async def add_entry(self, ip: str, method: str, endpoint: str,
                         status: int, size: int, ua: str = "", referer: str = ""):
        async with self._lock:
            now = time.time()
            self._entries.append((now, ip, method, endpoint, status, size, ua, referer))
            self._batch_queue.append((ip, method, endpoint, status, size, ua, referer))

    async def set_network_stats(self, active_connections: int, rx_bytes: int, tx_bytes: int):
        async with self._lock:
            self._active_connections = active_connections
            self._bandwidth_rx += rx_bytes
            self._bandwidth_tx += tx_bytes

    async def drain_batch(self) -> Optional[dict]:
        """Pop batch queue and build aggregate snapshot. Returns None if empty."""
        async with self._lock:
            if not self._batch_queue and not self._bandwidth_rx:
                return None

            # Compute snapshot from sliding window
            now = time.time()
            cutoff = now - self.window
            window_entries = [e for e in self._entries if e[0] >= cutoff]

            if not window_entries:
                return None

            total = len(window_entries)
            rps = round(total / self.window, 2) if self.window > 0 else 0

            # Status code counts
            status_counts = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
            for e in window_entries:
                s = e[4]
                if 200 <= s < 300:
                    status_counts["2xx"] += 1
                elif 300 <= s < 400:
                    status_counts["3xx"] += 1
                elif 400 <= s < 500:
                    status_counts["4xx"] += 1
                elif s >= 500:
                    status_counts["5xx"] += 1

            error_count = status_counts["5xx"]
            error_rate = round((error_count / total) * 100, 2) if total > 0 else 0.0

            # Top IPs
            ip_counts: Dict[str, int] = defaultdict(int)
            endpoint_counts: Dict[str, int] = defaultdict(int)
            for e in window_entries:
                ip_counts[e[1]] += 1
                endpoint_counts[e[3]] += 1

            top_ips = sorted(ip_counts.items(), key=lambda x: -x[1])[:20]
            top_endpoints = sorted(endpoint_counts.items(), key=lambda x: -x[1])[:20]

            # Bandwidth
            bandwidth_bytes = self._bandwidth_rx + self._bandwidth_tx

            # Alerts
            alerts = self._check_alerts(rps, error_count, top_ips)

            snapshot = {
                "rps": rps,
                "error_rate": error_rate,
                "active_connections": self._active_connections,
                "total_requests": total,
                "bandwidth_bytes": bandwidth_bytes,
                "top_ips": [{"ip": ip, "count": cnt} for ip, cnt in top_ips],
                "top_endpoints": [{"endpoint": ep, "count": cnt} for ep, cnt in top_endpoints],
                "status_code_counts": status_counts,
                "alerts": alerts,
            }

            # Reset counters (keep window entries for next cycle)
            self._bandwidth_rx = 0
            self._bandwidth_tx = 0

            return snapshot

    def _check_alerts(self, rps: float, error_count: int, top_ips: list) -> List[dict]:
        """Check thresholds and return alert list."""
        alerts = []
        now = time.time()
        cooldown = 30  # seconds between same alert type

        if rps > settings.traffic_rps_threshold:
            key = "rps_spike"
            if now - self._last_alerts.get(key, 0) > cooldown:
                alerts.append({"type": "rps_spike", "severity": "warning",
                               "message": f"RPS spike: {rps:.1f} (threshold: {settings.traffic_rps_threshold})"})
                self._last_alerts[key] = now

        if error_count > settings.traffic_5xx_threshold:
            key = "5xx_flood"
            if now - self._last_alerts.get(key, 0) > cooldown:
                alerts.append({"type": "5xx_flood", "severity": "critical",
                               "message": f"5xx errors: {error_count} in {self.window}s (threshold: {settings.traffic_5xx_threshold})"})
                self._last_alerts[key] = now

        for ip, cnt in top_ips:
            if cnt > settings.traffic_single_ip_threshold:
                key = f"ip_flood_{ip}"
                if now - self._last_alerts.get(key, 0) > cooldown:
                    alerts.append({"type": "ip_flood", "severity": "warning",
                                   "message": f"IP flood detected: {ip} — {cnt} requests in {self.window}s"})
                    self._last_alerts[key] = now
                    break  # one IP alert per cycle

        return alerts

    async def flush_batch_to_db(self, max_retries: int = 3) -> int:
        """Write queued raw entries to DB. Returns count written."""
        async with self._lock:
            batch = list(self._batch_queue)
            # Build aggregate snapshot (pass None for drain without reset)
            agg = await self._drain_aggregate_only()

        if not batch and not agg:
            return 0

        written = 0
        for attempt in range(max_retries):
            try:
                async with async_session() as session:
                    # Batch insert raw logs
                    for ip, method, endpoint, status, size, ua, referer in batch:
                        session.add(TrafficLog(
                            timestamp=datetime.now(timezone.utc),
                            ip=ip,
                            method=method,
                            endpoint=endpoint[:512],
                            status_code=status,
                            response_size=size,
                            user_agent=ua[:512] if ua else None,
                            referer=referer[:512] if referer else None,
                        ))
                        written += 1

                    # Insert aggregate
                    if agg:
                        session.add(TrafficAggregate(**agg))

                    await session.commit()

                async with self._lock:
                    self._batch_queue = self._batch_queue[len(batch):]
                break  # success
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Traffic DB flush error (attempt {attempt+1}/{max_retries}): {e}")
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"Traffic DB flush failed after {max_retries} attempts: {e}")

        return written

    async def _drain_aggregate_only(self) -> Optional[dict]:
        """Same as drain_batch but does NOT reset bandwidth (called from flush)."""
        now = time.time()
        cutoff = now - self.window
        window_entries = [e for e in self._entries if e[0] >= cutoff]

        if not window_entries:
            return None

        total = len(window_entries)
        rps = round(total / self.window, 2) if self.window > 0 else 0

        status_counts = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
        for e in window_entries:
            s = e[4]
            if 200 <= s < 300:
                status_counts["2xx"] += 1
            elif 300 <= s < 400:
                status_counts["3xx"] += 1
            elif 400 <= s < 500:
                status_counts["4xx"] += 1
            elif s >= 500:
                status_counts["5xx"] += 1

        error_count = status_counts["5xx"]
        error_rate = round((error_count / total) * 100, 2) if total > 0 else 0.0

        ip_counts: Dict[str, int] = defaultdict(int)
        endpoint_counts: Dict[str, int] = defaultdict(int)
        for e in window_entries:
            ip_counts[e[1]] += 1
            endpoint_counts[e[3]] += 1

        top_ips = sorted(ip_counts.items(), key=lambda x: -x[1])[:20]
        top_endpoints = sorted(endpoint_counts.items(), key=lambda x: -x[1])[:20]

        # bandwidth was already reset by drain_batch, so use 0 for DB
        bw = 0

        return {
            "rps": rps,
            "error_rate": error_rate,
            "active_connections": self._active_connections,
            "total_requests": total,
            "bandwidth_bytes": bw,
            "top_ips": [{"ip": ip, "count": cnt} for ip, cnt in top_ips],
            "top_endpoints": [{"endpoint": ep, "count": cnt} for ep, cnt in top_endpoints],
            "status_code_counts": status_counts,
            "alerts": None,
        }

    async def get_live_snapshot(self) -> dict:
        """Get current live snapshot without draining (for WebSocket / REST)."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window
            window_entries = [e for e in self._entries if e[0] >= cutoff]

            total = len(window_entries)
            rps = round(total / self.window, 2) if self.window > 0 else 0

            status_counts = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
            for e in window_entries:
                s = e[4]
                if 200 <= s < 300:
                    status_counts["2xx"] += 1
                elif 300 <= s < 400:
                    status_counts["3xx"] += 1
                elif 400 <= s < 500:
                    status_counts["4xx"] += 1
                elif s >= 500:
                    status_counts["5xx"] += 1

            error_count = status_counts["5xx"]
            error_rate = round((error_count / total) * 100, 2) if total > 0 else 0.0

            ip_counts: Dict[str, int] = defaultdict(int)
            endpoint_counts: Dict[str, int] = defaultdict(int)
            for e in window_entries:
                ip_counts[e[1]] += 1
                endpoint_counts[e[3]] += 1

            top_ips = sorted(ip_counts.items(), key=lambda x: -x[1])[:20]
            top_endpoints = sorted(endpoint_counts.items(), key=lambda x: -x[1])[:20]
            total_bw = self._bandwidth_rx + self._bandwidth_tx

        return {
            "rps": rps,
            "error_rate": error_rate,
            "active_connections": self._active_connections,
            "total_requests": total,
            "bandwidth_bytes": total_bw,
            "top_ips": [{"ip": ip, "count": cnt} for ip, cnt in top_ips],
            "top_endpoints": [{"endpoint": ep, "count": cnt} for ep, cnt in top_endpoints],
            "status_code_counts": status_counts,
        }


# ── Global state singleton ──────────────────────────────────────────────

traffic_state = TrafficState(
    window_seconds=settings.traffic_window_seconds,
    batch_interval=settings.traffic_batch_interval,
)


# ── Log tailer ──────────────────────────────────────────────────────────

async def _tail_file(filepath: str):
    """Async generator that tails a log file line by line."""
    if not os.path.exists(filepath):
        logger.warning(f"Log file not found: {filepath}")
        return

    with open(filepath, "r") as f:
        # Seek to end
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            yield line.strip()


async def _parse_and_enqueue(line: str):
    """Parse a log line and push to traffic state."""
    match = NGINX_PATTERN.match(line)
    if not match:
        return

    ip = match.group("ip")
    method = match.group("method")
    endpoint = match.group("endpoint")
    status = int(match.group("status"))
    size = int(match.group("size"))
    referer = match.group("referer")
    ua = match.group("ua")

    await traffic_state.add_entry(ip, method, endpoint, status, size, ua, referer)


async def tail_logs_loop():
    """Background task: tail all configured access logs."""
    paths = settings.traffic_log_paths
    if not paths:
        logger.info("No access log paths found; traffic log tailing disabled")
        return

    logger.info(f"Starting traffic log tailer for: {paths}")

    async def tail_one(path: str):
        async for line in _tail_file(path):
            await _parse_and_enqueue(line)

    tasks = [asyncio.create_task(tail_one(p)) for p in paths]
    await asyncio.gather(*tasks)


# ── Network monitor ─────────────────────────────────────────────────────

async def _run_cmd(*args: str) -> str:
    """Run a shell command and return stdout."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() if stdout else ""


def _parse_ss_output(output: str) -> int:
    """Count lines from `ss -tunap` output, minus the header."""
    lines = output.split("\n")
    return max(0, len(lines) - 1)


def _parse_proc_net_dev(output: str, last_rx: dict, last_tx: dict) -> tuple:
    """
    Parse /proc/net/dev, return (total_rx_delta, total_tx_delta, new_last_rx, new_last_tx).
    """
    lines = output.split("\n")
    total_rx = 0
    total_tx = 0
    new_last_rx = {}
    new_last_tx = {}

    for line in lines:
        if ":" not in line or "Inter-|" in line or "face" in line:
            continue
        parts = line.strip().split()
        iface = parts[0].rstrip(":")
        if iface == "lo":
            continue  # skip loopback
        rx_bytes = int(parts[1])
        tx_bytes = int(parts[9])

        # Delta from last read
        delta_rx = rx_bytes - last_rx.get(iface, rx_bytes)
        delta_tx = tx_bytes - last_tx.get(iface, tx_bytes)

        # Handle counter wrap (reset)
        if delta_rx < 0:
            delta_rx = rx_bytes
        if delta_tx < 0:
            delta_tx = tx_bytes

        total_rx += delta_rx
        total_tx += delta_tx
        new_last_rx[iface] = rx_bytes
        new_last_tx[iface] = tx_bytes

    return total_rx, total_tx, new_last_rx, new_last_tx


async def network_monitor_loop():
    """Background task: collect ss + /proc/net/dev every 2 seconds."""
    logger.info("Starting network traffic monitor")

    while True:
        try:
            # Active connections
            ss_out = await _run_cmd("ss", "-tunap")
            conn_count = _parse_ss_output(ss_out)

            # Bandwidth via /proc/net/dev
            try:
                with open("/proc/net/dev", "r") as f:
                    dev_out = f.read()
                rx_delta, tx_delta, traffic_state._last_rx_bytes, traffic_state._last_tx_bytes = \
                    _parse_proc_net_dev(dev_out, traffic_state._last_rx_bytes, traffic_state._last_tx_bytes)
            except FileNotFoundError:
                rx_delta = tx_delta = 0

            await traffic_state.set_network_stats(conn_count, rx_delta, tx_delta)

        except Exception as e:
            logger.error(f"Network monitor error: {e}")

        await asyncio.sleep(2)


# ── DB flusher ──────────────────────────────────────────────────────────

async def db_flusher_loop():
    """Periodically flush batch queue to SQLite."""
    logger.info(f"Starting traffic DB flusher (interval: {settings.traffic_batch_interval}s)")

    while True:
        await asyncio.sleep(settings.traffic_batch_interval)
        try:
            count = await traffic_state.flush_batch_to_db()
            if count:
                logger.debug(f"Flushed {count} traffic log entries to DB")
        except Exception as e:
            logger.error(f"Traffic DB flush error: {e}")


# ── DB cleanup ──────────────────────────────────────────────────────────

async def db_cleanup_loop():
    """Periodically prune old data according to retention policy."""
    from sqlalchemy import delete

    logger.info(f"Starting traffic DB cleanup "
                f"(raw: {settings.traffic_raw_retention_hours}h, agg: {settings.traffic_agg_retention_days}d)")

    while True:
        await asyncio.sleep(3600)  # run every hour
        try:
            raw_cutoff = datetime.now(timezone.utc).timestamp() - settings.traffic_raw_retention_hours * 3600
            agg_cutoff = datetime.now(timezone.utc).timestamp() - settings.traffic_agg_retention_days * 86400

            async with async_session() as session:
                # Delete old raw logs
                result = await session.execute(
                    delete(TrafficLog).where(TrafficLog.timestamp < datetime.fromtimestamp(raw_cutoff, tz=timezone.utc))
                )
                await session.commit()
                logger.info(f"Pruned {result.rowcount} old traffic logs")

                # Delete old aggregates
                result = await session.execute(
                    delete(TrafficAggregate).where(TrafficAggregate.timestamp < datetime.fromtimestamp(agg_cutoff, tz=timezone.utc))
                )
                await session.commit()
                logger.info(f"Pruned {result.rowcount} old traffic aggregates")

        except Exception as e:
            logger.error(f"Traffic DB cleanup error: {e}")


# ── Main entry point ───────────────────────────────────────────────────

async def start_traffic_monitoring():
    """Start all background tasks for traffic monitoring if enabled."""
    if not settings.traffic_monitoring_enabled:
        logger.info("Traffic monitoring is disabled")
        return

    tasks = []

    # If log files exist, start log tailer
    if settings.traffic_log_paths:
        tasks.append(asyncio.create_task(tail_logs_loop()))

    # Always start network monitor and DB flusher
    tasks.append(asyncio.create_task(network_monitor_loop()))
    tasks.append(asyncio.create_task(db_flusher_loop()))
    tasks.append(asyncio.create_task(db_cleanup_loop()))

    if tasks:
        logger.info(f"Started {len(tasks)} traffic monitoring background tasks")
        await asyncio.gather(*tasks)