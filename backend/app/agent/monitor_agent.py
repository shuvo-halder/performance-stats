#!/usr/bin/env python3
"""
Server Stats Monitoring Agent.
Collects system metrics and pushes to central API.
Runs on Linux servers as a lightweight daemon.

Usage:
  python3 monitor_agent.py --server https://api.example.com --token YOUR_TOKEN
  python3 monitor_agent.py --config /etc/server-stats-agent.conf
"""

import os
import sys
import json
import time
import socket
import platform
import hashlib
import hmac
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

try:
    import psutil
except ImportError:
    print("ERROR: psutil is required. Install with: pip install psutil")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests")
    sys.exit(1)

# ── Configuration ────────────────────────────────────────────────────
DEFAULT_CONFIG_PATH = "/etc/server-stats-agent.conf"
DEFAULT_COLLECT_INTERVAL = 60
DEFAULT_HEARTBEAT_INTERVAL = 30
DEFAULT_API_TIMEOUT = 10
MAX_RETRIES = 3


class AgentConfig:
    def __init__(self, server_url: str = "", token: str = ""):
        self.server_url = server_url.rstrip("/")
        self.agent_token = token
        self.collect_interval = DEFAULT_COLLECT_INTERVAL
        self.heartbeat_interval = DEFAULT_HEARTBEAT_INTERVAL
        self.api_timeout = DEFAULT_API_TIMEOUT
        self.hostname = socket.gethostname()
        self.log_file = "/var/log/server-stats-agent.log"
        self.pid_file = "/var/run/server-stats-agent.pid"

    @classmethod
    def from_file(cls, path: str = DEFAULT_CONFIG_PATH) -> "AgentConfig":
        cfg = cls()
        config_data = {}
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        config_data[key.strip()] = val.strip()
        except FileNotFoundError:
            pass

        cfg.server_url = config_data.get("SERVER_URL", cfg.server_url)
        cfg.agent_token = config_data.get("AGENT_TOKEN", cfg.agent_token)
        cfg.collect_interval = int(config_data.get("COLLECT_INTERVAL", cfg.collect_interval))
        cfg.heartbeat_interval = int(config_data.get("HEARTBEAT_INTERVAL", cfg.heartbeat_interval))
        return cfg

    @classmethod
    def from_args(cls) -> "AgentConfig":
        parser = argparse.ArgumentParser(description="Server Stats Monitoring Agent")
        parser.add_argument("--server", help="Central API server URL")
        parser.add_argument("--token", help="Agent authentication token")
        parser.add_argument("--config", help=f"Config file path (default: {DEFAULT_CONFIG_PATH})")
        parser.add_argument("--interval", type=int, default=DEFAULT_COLLECT_INTERVAL, help="Collection interval in seconds")
        parser.add_argument("--daemon", action="store_true", help="Run as daemon")
        args = parser.parse_args()

        cfg = cls()
        if args.config:
            cfg = cls.from_file(args.config)
        if args.server:
            cfg.server_url = args.server
        if args.token:
            cfg.agent_token = args.token
        if args.interval:
            cfg.collect_interval = args.interval
        return cfg


# ── Metrics Collector ────────────────────────────────────────────────

class MetricsCollector:
    """Collects system metrics using psutil."""

    @staticmethod
    def collect() -> Dict:
        try:
            cpu = psutil.cpu_percent(interval=1)
        except Exception:
            cpu = 0
        try:
            mem = psutil.virtual_memory()
        except Exception:
            mem = type('obj', (object,), {'total': 0, 'used': 0, 'percent': 0})()

        load = [0, 0, 0]
        try:
            load = [x / psutil.cpu_count() * 100 if psutil.cpu_count() else 0 for x in psutil.getloadavg()]
        except Exception:
            pass

        disk_data = []
        try:
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_data.append({
                        "mount": part.mountpoint, "device": part.device,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "usage_percent": usage.percent,
                    })
                except (PermissionError, OSError):
                    continue
        except Exception:
            pass

        services = []
        try:
            import subprocess
            for svc in ["nginx", "docker", "mysql", "postgresql", "redis", "apache2"]:
                try:
                    r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
                    services.append({"name": svc, "status": r.stdout.strip()})
                except Exception:
                    services.append({"name": svc, "status": "unknown"})
        except Exception:
            pass

        processes = []
        try:
            for proc in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                               key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:5]:
                processes.append({
                    "pid": proc.info["pid"], "name": proc.info["name"],
                    "cpu_percent": round(proc.info.get("cpu_percent", 0) or 0, 1),
                    "mem_percent": round(proc.info.get("memory_percent", 0) or 0, 1),
                })
        except Exception:
            pass

        swap = {"total_mb": 0, "used_mb": 0, "percent": 0}
        try:
            s = psutil.swap_memory()
            swap = {"total_mb": round(s.total / (1024*1024), 1),
                    "used_mb": round(s.used / (1024*1024), 1), "percent": s.percent}
        except Exception:
            pass

        net_conns = 0
        try:
            net_conns = len(psutil.net_connections())
        except (psutil.AccessDenied, PermissionError):
            pass

        return {
            "cpu_percent": round(cpu, 1),
            "mem_total_mb": round(mem.total / (1024*1024), 1) if mem.total else 0,
            "mem_used_mb": round(mem.used / (1024*1024), 1) if mem.used else 0,
            "mem_percent": round(mem.percent, 1),
            "disk_data": disk_data,
            "load_1m": round(load[0], 2),
            "load_5m": round(load[1], 2),
            "load_15m": round(load[2], 2),
            "network_connections": net_conns,
            "top_processes": processes,
            "services_data": services,
            "swap_total_mb": swap["total_mb"],
            "swap_used_mb": swap["used_mb"],
            "swap_percent": swap["percent"],
        }


# ── Agent Core ───────────────────────────────────────────────────────

class MonitorAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self._running = True
        self._local_cache: list = []
        self._collector = MetricsCollector()
        self._setup_logging()
        self._heartbeat_count = 0

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.config.log_file) if self.config.log_file else logging.StreamHandler(),
            ] if self.config.log_file else [logging.StreamHandler()],
        )
        self.logger = logging.getLogger("agent")

    def _sign_request(self, data: dict) -> str:
        """HMAC-SHA256 signature for request authentication."""
        message = json.dumps(data, sort_keys=True)
        return hmac.new(
            self.config.agent_token.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    def _send_request(self, endpoint: str, data: dict) -> bool:
        """Send data to central API with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                signature = self._sign_request(data)
                resp = requests.post(
                    f"{self.config.server_url}{endpoint}",
                    json=data,
                    headers={
                        "X-Agent-Token": self.config.agent_token,
                        "X-Signature": signature,
                        "Content-Type": "application/json",
                    },
                    timeout=self.config.api_timeout,
                )
                if resp.status_code == 200:
                    return True
                elif resp.status_code == 401:
                    self.logger.error("Authentication failed — check agent token")
                    return False
                else:
                    self.logger.warning(f"API returned {resp.status_code} (attempt {attempt+1})")
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timed out (attempt {attempt+1})")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection failed (attempt {attempt+1})")
            except Exception as e:
                self.logger.error(f"Request error: {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

        # Cache locally if all retries failed
        self._local_cache.append({"endpoint": endpoint, "data": data, "time": time.time()})
        self.logger.warning(f"Request failed after {MAX_RETRIES} attempts — cached locally")
        return False

    def _flush_cache(self):
        """Attempt to flush locally cached data."""
        if not self._local_cache:
            return
        self.logger.info(f"Flushing {len(self._local_cache)} cached items...")
        remaining = []
        for item in self._local_cache:
            if self._send_request(item["endpoint"], item["data"]):
                continue  # Sent successfully
            remaining.append(item)
        self._local_cache = remaining

    def run(self):
        """Main agent loop."""
        self.logger.info(f"Server Stats Agent v1.0 started on {self.config.hostname}")
        self.logger.info(f"Server: {self.config.server_url}")
        self.logger.info(f"Interval: {self.config.collect_interval}s | Heartbeat: {self.config.heartbeat_interval}s")

        # Handle termination
        signal.signal(signal.SIGTERM, lambda *_: self._stop())
        signal.signal(signal.SIGINT, lambda *_: self._stop())

        last_collect = 0
        last_heartbeat = 0

        while self._running:
            now = time.time()

            # Collect and send metrics
            if now - last_collect >= self.config.collect_interval:
                try:
                    metrics = self._collector.collect()
                    self._send_request("/servers/metrics", metrics)
                    self._flush_cache()
                    last_collect = now
                except Exception as e:
                    self.logger.error(f"Collection error: {e}")

            # Send heartbeat
            if now - last_heartbeat >= self.config.heartbeat_interval:
                self._heartbeat_count += 1
                self._send_request("/api/health", {
                    "hostname": self.config.hostname,
                    "heartbeat": self._heartbeat_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                last_heartbeat = now

            time.sleep(1)

        self.logger.info("Agent stopped")

    def _stop(self):
        self._running = False


# ── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    config = AgentConfig.from_args()
    if not config.server_url or not config.agent_token:
        print("ERROR: --server and --token are required (or config file)")
        print("Usage: python3 monitor_agent.py --server https://api.example.com --token YOUR_TOKEN")
        sys.exit(1)

    agent = MonitorAgent(config)
    agent.run()