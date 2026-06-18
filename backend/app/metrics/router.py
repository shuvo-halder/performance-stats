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


async def _collect_and_smooth() -> dict:
    """Collect all metrics and apply smoothing."""
    metrics, auto_restart = await collect_all_metrics()

    # Extract key metrics for smoothing
    smoothable = {
        "cpu_usage_percent": metrics.get("cpu_usage_percent", 0),
        "mem_usage_percent": metrics.get("mem_usage_percent", 0),
        "cpu_load_1min": metrics.get("cpu_load_1min", 0),
        "cpu_load_5min": metrics.get("cpu_load_5min", 0),
        "cpu_load_15min": metrics.get("cpu_load_15min", 0),
    }

    smoothed = await smoother.get_all_smoothed(smoothable)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw": metrics,
        "smoothed": smoothed,
        "auto_restart_results": auto_restart,
    }


async def _collect_deep_network() -> dict:
    """Collect deep network metrics."""
    await deep_network.collect()
    return await deep_network.get_snapshot()


async def _collect_disk_iops() -> dict:
    """Collect disk IOPS metrics."""
    await disk_iops.collect()
    return await disk_iops.get_snapshot()


@router.get("/current")
async def get_current_metrics():
    """Get current system metrics with raw + smoothed values."""
    try:
        data = await _collect_and_smooth()

        # Add deep network and disk IOPS
        net = await _collect_deep_network()
        disk = await _collect_disk_iops()

        data["network_deep"] = net
        data["disk_iops"] = disk

        return data
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {"error": str(e)}


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
    """Get deep network insight data."""
    try:
        data = await _collect_deep_network()
        return data
    except Exception as e:
        logger.error(f"Error collecting deep network: {e}")
        return {"error": str(e)}


@router.get("/disk/iops")
async def get_disk_iops():
    """Get disk IOPS metrics."""
    try:
        data = await _collect_disk_iops()
        return data
    except Exception as e:
        logger.error(f"Error collecting disk IOPS: {e}")
        return {"error": str(e)}


# ── WebSocket ──────────────────────────────────────────────────────────

@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket pushing real-time metrics every 2 seconds."""
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

            # Collect and push all metrics
            try:
                data = await _collect_and_smooth()
                net = await _collect_deep_network()
                disk = await _collect_disk_iops()
                data["network_deep"] = net
                data["disk_iops"] = disk

                await websocket.send_text(json.dumps({
                    "type": "metrics_snapshot",
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }))
            except Exception as e:
                logger.error(f"Metrics WebSocket collect error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e),
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