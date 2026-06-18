"""
Metrics Router for Grafana-inspired Dashboard.

Endpoints:
  GET  /metrics/current       — Current system metrics with smoothing
  GET  /metrics/history       — Historical time-series data
  GET  /metrics/network/deep  — Deep network insight
  GET  /metrics/disk/iops     — Disk IOPS monitoring
  WS   /ws/metrics            — Real-time push every 2 seconds
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select, desc

from app.database import async_session, Snapshot
from app.collectors import collect_all_metrics
from app.metrics.smoothing import smoother
from app.metrics.network_deep import deep_network
from app.metrics.disk_iops import disk_iops
from app.config import settings

logger = logging.getLogger("server-stats.metrics.router")

router = APIRouter(prefix="/metrics", tags=["metrics"])

# ── Live Metrics State (continuously collected by background task) ────
_live_metrics: dict = {
    "timestamp": None,
    "raw": {},
    "smoothed": {},
    "network_deep": {"total_connections": 0, "connection_states": {}, "top_ips": [], "port_counts": [], "connection_rate": 0},
    "disk_iops": {"read_iops": 0, "write_iops": 0, "read_mb_s": 0, "write_mb_s": 0, "devices": []},
}
_live_lock = asyncio.Lock()
_background_task = None


async def _background_collection_loop():
    """Continuously collect metrics every 3 seconds in background."""
    while True:
        try:
            await _update_live_metrics()
        except Exception as e:
            logger.error(f"Background collection error: {e}")
        await asyncio.sleep(3)


async def _update_live_metrics():
    """Update live metrics state with fresh data from all collectors.
    
    Each collector is wrapped in its own try/except so a failure in one
    doesn't prevent others from updating. Default/empty values are used
    on failure.
    """
    # 1. System metrics
    try:
        metrics, auto_restart = await collect_all_metrics()
    except Exception as e:
        logger.error(f"System metrics error: {e}")
        metrics = {}
        auto_restart = []

    # 2. Smoothing
    smoothed = {}
    try:
        smoothable = {
            "cpu_usage_percent": metrics.get("cpu_usage_percent", 0),
            "mem_usage_percent": metrics.get("mem_usage_percent", 0),
            "cpu_load_1min": metrics.get("cpu_load_1min", 0),
            "cpu_load_5min": metrics.get("cpu_load_5min", 0),
            "cpu_load_15min": metrics.get("cpu_load_15min", 0),
        }
        smoothed = await smoother.get_all_smoothed(smoothable)
    except Exception as e:
        logger.error(f"Smoothing error: {e}")

    # 3. Deep network (collects via ss or psutil, fails gracefully)
    net = {"total_connections": 0, "connection_states": {}, "top_ips": [], "port_counts": [], "connection_rate": 0}
    try:
        await deep_network.collect()
        net = await deep_network.get_snapshot()
    except Exception as e:
        logger.error(f"Network error: {e}")

    # 4. Disk IOPS (collects via /proc/diskstats or psutil, fails gracefully)
    dsk = {"read_iops": 0, "write_iops": 0, "read_mb_s": 0, "write_mb_s": 0, "devices": []}
    try:
        await disk_iops.collect()
        dsk = await disk_iops.get_snapshot()
    except Exception as e:
        logger.error(f"Disk IOPS error: {e}")

    async with _live_lock:
        _live_metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
        _live_metrics["raw"] = metrics
        _live_metrics["smoothed"] = smoothed
        _live_metrics["network_deep"] = net
        _live_metrics["disk_iops"] = dsk
        _live_metrics["auto_restart_results"] = auto_restart


async def start_background_collection():
    """Start the background collection loop."""
    global _background_task
    if _background_task is None:
        # Do an immediate first collection so data is available right away
        await _update_live_metrics()
        _background_task = asyncio.create_task(_background_collection_loop())
        logger.info("Background metrics collection started")


async def stop_background_collection():
    """Stop the background collection loop."""
    global _background_task
    if _background_task:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
        _background_task = None
        logger.info("Background metrics collection stopped")


# ── REST Endpoints ────────────────────────────────────────────────────


@router.get("/current")
async def get_current_metrics():
    """
    Get current system metrics with raw + smoothed values.
    
    Returns instantly from the continuously-updated live state.
    The background task collects fresh data every 3 seconds from:
      - psutil (CPU, memory, disk, network)
      - ss -tun or psutil (deep network insight)
      - /proc/diskstats or psutil (disk IOPS)
    """
    async with _live_lock:
        return dict(_live_metrics)


@router.get("/history")
async def get_metrics_history(
    period: str = Query("1h", description="Time period: 15m, 1h, 6h, 24h"),
):
    """Get historical time-series data from snapshots."""
    now = datetime.now(timezone.utc)
    period_map = {
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
    }
    delta = period_map.get(period, timedelta(hours=1))
    cutoff = now - delta

    async with async_session() as session:
        result = await session.execute(
            select(Snapshot)
            .where(Snapshot.timestamp >= cutoff)
            .order_by(Snapshot.timestamp.asc())
        )
        rows = result.scalars().all()

    history = []
    for row in rows:
        history.append({
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "cpu_usage_percent": row.cpu_usage_percent,
            "cpu_load_1min": row.cpu_load_1min,
            "cpu_load_5min": row.cpu_load_5min,
            "cpu_load_15min": row.cpu_load_15min,
            "mem_usage_percent": row.mem_usage_percent,
            "mem_total_mb": row.mem_total_mb,
            "mem_used_mb": row.mem_used_mb,
            "network_connections": row.network_connections,
        })

    return {"period": period, "count": len(history), "data": history}


@router.get("/network/deep")
async def get_network_deep():
    """Get deep network insight data (collects fresh on demand)."""
    try:
        await deep_network.collect()
        return await deep_network.get_snapshot()
    except Exception as e:
        logger.error(f"Error collecting deep network: {e}")
        return {"error": str(e)}


@router.get("/disk/iops")
async def get_disk_iops():
    """Get disk IOPS metrics (collects fresh on demand)."""
    try:
        await disk_iops.collect()
        return await disk_iops.get_snapshot()
    except Exception as e:
        logger.error(f"Error collecting disk IOPS: {e}")
        return {"error": str(e)}


# ── WebSocket ──────────────────────────────────────────────────────────

@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket pushing live metrics every 2 seconds from the curated state."""
    await websocket.accept()
    logger.info("Metrics WebSocket connected")

    try:
        while True:
            try:
                msg = await asyncio.wait_for(
                    websocket.receive_text(), timeout=2.0
                )
                if msg == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            # Push current live state
            async with _live_lock:
                payload = dict(_live_metrics)

            await websocket.send_text(json.dumps({
                "type": "metrics_snapshot",
                "data": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))

    except WebSocketDisconnect:
        logger.info("Metrics WebSocket disconnected")
    except Exception as e:
        logger.error(f"Metrics WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass