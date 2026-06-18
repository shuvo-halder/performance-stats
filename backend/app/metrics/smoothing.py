"""
Advanced Smoothing Engine for Real-time Metrics.

Provides:
  - Exponential Moving Average (EMA) with configurable alpha
  - Rolling (simple moving) average with configurable window
  - In-memory deque storage per metric
  - Toggle between raw / smoothed / rolling values
"""

import time
from collections import deque, OrderedDict
from typing import Dict, List, Optional, Tuple
import asyncio
import logging

logger = logging.getLogger("server-stats.metrics.smoothing")


class MetricSmoother:
    """
    Smooths metrics using EMA + Rolling average.
    Maintains a deque of recent raw values per metric key.
    """

    def __init__(self, window_size: int = 10, ema_alpha: float = 0.25):
        """
        Args:
            window_size: Number of samples for rolling average
            ema_alpha: Smoothing factor (0.0–1.0). Lower = smoother
        """
        self.window_size = window_size
        self.ema_alpha = ema_alpha
        self._lock = asyncio.Lock()
        # {metric_key: deque of (timestamp, value)}
        self._buffers: Dict[str, deque] = {}
        # {metric_key: last EMA value}
        self._ema_values: Dict[str, float] = {}

    async def push(self, key: str, value: float):
        """Push a new raw sample for a metric."""
        async with self._lock:
            if key not in self._buffers:
                self._buffers[key] = deque(maxlen=self.window_size)
            self._buffers[key].append((time.time(), value))

    async def get_raw(self, key: str) -> Optional[float]:
        """Get the latest raw value."""
        async with self._lock:
            buf = self._buffers.get(key)
            if not buf:
                return None
            return buf[-1][1]

    async def get_rolling(self, key: str) -> Optional[float]:
        """Get rolling (simple moving) average."""
        async with self._lock:
            buf = self._buffers.get(key)
            if not buf or len(buf) < 2:
                return buf[-1][1] if buf else None
            values = [v for _, v in buf]
            return sum(values) / len(values)

    async def get_ema(self, key: str, value: Optional[float] = None) -> Optional[float]:
        """Get Exponential Moving Average.
        If value is provided, updates EMA with new sample first.
        """
        async with self._lock:
            if value is not None:
                if key not in self._ema_values:
                    self._ema_values[key] = value
                else:
                    prev = self._ema_values[key]
                    self._ema_values[key] = value * self.ema_alpha + prev * (1.0 - self.ema_alpha)
            return self._ema_values.get(key)

    async def get_all(self, key: str, new_value: Optional[float] = None) -> dict:
        """
        Get raw, rolling, and EMA for a metric in one call.
        If new_value provided, updates buffers first.
        """
        if new_value is not None:
            await self.push(key, new_value)

        raw = await self.get_raw(key)
        rolling = await self.get_rolling(key)
        ema = await self.get_ema(key, new_value)

        return {
            "raw": raw,
            "rolling": rolling,
            "ema": ema,
            "key": key,
        }

    async def get_all_smoothed(self, values: Dict[str, float]) -> Dict[str, dict]:
        """
        Process a batch of metric values and return raw + smoothed for each.
        values = {"cpu_percent": 45.2, "mem_percent": 62.1, ...}
        Returns: {"cpu_percent": {"raw": 45.2, "rolling": 44.8, "ema": 44.9}, ...}
        """
        result = {}
        for key, val in values.items():
            result[key] = await self.get_all(key, new_value=val)
        return result

    async def get_history(self, key: str, count: int = 60) -> List[dict]:
        """Get last N raw samples with timestamps for charting."""
        async with self._lock:
            buf = self._buffers.get(key)
            if not buf:
                return []
            samples = list(buf)[-count:]
            return [{"t": ts, "v": v} for ts, v in samples]

    async def clear(self, key: Optional[str] = None):
        """Clear buffer for a specific key or all keys."""
        async with self._lock:
            if key:
                self._buffers.pop(key, None)
                self._ema_values.pop(key, None)
            else:
                self._buffers.clear()
                self._ema_values.clear()


# ── Global singleton ────────────────────────────────────────────────────
smoother = MetricSmoother(window_size=10, ema_alpha=0.25)