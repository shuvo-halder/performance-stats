"""
Disk IOPS Monitoring Collector.

Provides:
  - Read IOPS (operations/sec)
  - Write IOPS
  - Read throughput (MB/s)
  - Write throughput (MB/s)
  - Per-device stats
  - Delta-based rate calculation
"""

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("server-stats.metrics.disk")


class DiskIOPSCollector:
    """
    Collects disk IOPS and throughput metrics.
    Linux: parses /proc/diskstats
    Windows/macOS: uses psutil.disk_io_counters()
    Runs as a background task every 2 seconds.
    """

    def __init__(self):
        import platform
        self._lock = asyncio.Lock()
        self._is_linux = platform.system() == "Linux"
        # Previous raw values for delta calculation
        self._prev_stats: Dict[str, dict] = {}
        self._last_sample_time = 0.0

        # Smoothed rates (rolling buffer)
        self._read_iops_buffer: deque = deque(maxlen=15)
        self._write_iops_buffer: deque = deque(maxlen=15)
        self._read_mbs_buffer: deque = deque(maxlen=15)
        self._write_mbs_buffer: deque = deque(maxlen=15)

        # Current values
        self._read_iops = 0.0
        self._write_iops = 0.0
        self._read_mb_s = 0.0
        self._write_mb_s = 0.0
        self._devices: List[dict] = []
        self._total_reads = 0
        self._total_writes = 0
        self._total_read_mb = 0.0
        self._total_write_mb = 0.0

    async def collect(self):
        """Read disk stats and compute IOPS/throughput."""
        try:
            if self._is_linux:
                stats = self._parse_diskstats()
            else:
                stats = self._get_psutil_disk_stats()
            if not stats:
                return

            now = time.time()
            dt = now - self._last_sample_time if self._last_sample_time > 0 else 1.0
            self._last_sample_time = now

            total_read_ios = 0
            total_write_ios = 0
            total_read_sectors = 0
            total_write_sectors = 0
            devices = []

            for device, current in stats.items():
                prev = self._prev_stats.get(device, {})

                # Field layout (from /proc/diskstats):
                # 3 - reads completed
                # 7 - writes completed
                # 5 - sectors read
                # 9 - sectors written

                reads = current.get("reads", 0)
                writes = current.get("writes", 0)
                read_sectors = current.get("read_sectors", 0)
                write_sectors = current.get("write_sectors", 0)

                read_delta = reads - prev.get("reads", reads)
                write_delta = writes - prev.get("writes", writes)
                read_sec_delta = read_sectors - prev.get("read_sectors", read_sectors)
                write_sec_delta = write_sectors - prev.get("write_sectors", write_sectors)

                # Handle counter wrap
                if read_delta < 0:
                    read_delta = reads
                if write_delta < 0:
                    write_delta = writes
                if read_sec_delta < 0:
                    read_sec_delta = read_sectors
                if write_sec_delta < 0:
                    write_sec_delta = write_sectors

                # Per-second rates
                iops_read = read_delta / dt if dt > 0 else 0
                iops_write = write_delta / dt if dt > 0 else 0
                # Each sector = 512 bytes
                mb_read = (read_sec_delta * 512) / (1024 * 1024) / dt if dt > 0 else 0
                mb_write = (write_sec_delta * 512) / (1024 * 1024) / dt if dt > 0 else 0

                total_read_ios += read_delta
                total_write_ios += write_delta
                total_read_sectors += read_sec_delta
                total_write_sectors += write_sec_delta

                devices.append({
                    "device": device,
                    "read_iops": round(iops_read, 1),
                    "write_iops": round(iops_write, 1),
                    "read_mb_s": round(mb_read, 2),
                    "write_mb_s": round(mb_write, 2),
                })

            # Aggregate totals
            agg_read_iops = total_read_ios / dt if dt > 0 else 0
            agg_write_iops = total_write_ios / dt if dt > 0 else 0
            agg_read_mb = (total_read_sectors * 512) / (1024 * 1024) / dt if dt > 0 else 0
            agg_write_mb = (total_write_sectors * 512) / (1024 * 1024) / dt if dt > 0 else 0

            # Update rolling buffers
            self._read_iops_buffer.append(agg_read_iops)
            self._write_iops_buffer.append(agg_write_iops)
            self._read_mbs_buffer.append(agg_read_mb)
            self._write_mbs_buffer.append(agg_write_mb)

            # Compute smoothed values
            async with self._lock:
                self._read_iops = sum(self._read_iops_buffer) / len(self._read_iops_buffer)
                self._write_iops = sum(self._write_iops_buffer) / len(self._write_iops_buffer)
                self._read_mb_s = sum(self._read_mbs_buffer) / len(self._read_mbs_buffer)
                self._write_mb_s = sum(self._write_mbs_buffer) / len(self._write_mbs_buffer)
                self._devices = devices
                self._total_reads += total_read_ios
                self._total_writes += total_write_ios
                self._total_read_mb += (total_read_sectors * 512) / (1024 * 1024)
                self._total_write_mb += (total_write_sectors * 512) / (1024 * 1024)

            # Store current for next delta
            self._prev_stats = stats

        except Exception as e:
            logger.error(f"Disk IOPS collect error: {e}")

    def _parse_diskstats(self) -> Dict[str, dict]:
        """Parse /proc/diskstats and return per-device stats."""
        try:
            with open("/proc/diskstats", "r") as f:
                content = f.read()
        except FileNotFoundError:
            logger.warning("/proc/diskstats not available on this system")
            return {}
        except Exception as e:
            logger.error(f"Error reading /proc/diskstats: {e}")
            return {}

        stats = {}
        for line in content.strip().split("\n"):
            parts = line.split()
            if len(parts) < 14:
                continue

            device = parts[2]
            # Skip partitions, only track physical devices and common ones
            # Physical devices are typically sdX, nvmeX, vdX, xvdX
            if not any(device.startswith(p) for p in ["sd", "nvme", "vd", "xvd", "mmcblk", "loop"]):
                continue
            # Skip numeric suffixes (partitions) for NVMe (nvme0n1p1)
            if "nvme" in device:
                # Keep nvme0n1 but skip nvme0n1p1
                if len(device) > 6 and device[-1].isdigit() and device[-2].isalpha():
                    pass  # This is a valid NVMe device
                elif device[-1].isdigit() and device[-2].isdigit():
                    if device.count("n") == 1:
                        continue  # Skip partitions
            elif device[-1].isdigit() and device != "loop0":
                # This is likely a partition (sda1, vda1)
                continue

            stats[device] = {
                "reads": int(parts[3]),
                "read_sectors": int(parts[5]),
                "writes": int(parts[7]),
                "write_sectors": int(parts[9]),
            }

        return stats

    def _get_psutil_disk_stats(self) -> Dict[str, dict]:
        """Get disk stats on non-Linux platforms using psutil."""
        import psutil
        try:
            counter = psutil.disk_io_counters(perdisk=True)
        except Exception as e:
            logger.error(f"psutil.disk_io_counters() failed: {e}")
            return {}

        stats = {}
        for device, data in counter.items():
            stats[device] = {
                "reads": data.read_count,
                "read_sectors": data.read_bytes // 512,  # Convert bytes to sectors
                "writes": data.write_count,
                "write_sectors": data.write_bytes // 512,
            }
        return stats

    async def get_snapshot(self) -> dict:
        """Get current disk IOPS snapshot."""
        async with self._lock:
            return {
                "read_iops": round(self._read_iops, 1),
                "write_iops": round(self._write_iops, 1),
                "read_mb_s": round(self._read_mb_s, 2),
                "write_mb_s": round(self._write_mb_s, 2),
                "devices": self._devices,
                "total_reads": self._total_reads,
                "total_writes": self._total_writes,
                "total_read_mb": round(self._total_read_mb, 1),
                "total_write_mb": round(self._total_write_mb, 1),
            }


# ── Global singleton ────────────────────────────────────────────────────
disk_iops = DiskIOPSCollector()