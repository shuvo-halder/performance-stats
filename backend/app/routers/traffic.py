"""
Traffic monitoring router.

Endpoints:
  GET  /traffic/live     — current live snapshot
  GET  /traffic/history  — time-series aggregates from DB
  WS   /ws/traffic       — real-time push every 2 seconds
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy import select, desc

from app.database import async_session, TrafficAggregate
from app.collectors.traffic import traffic_state
from app.auth import get_current_user_optional

logger = logging.getLogger("server-stats.traffic.router")

router = APIRouter(tags=["traffic"])


# ── REST endpoints ──────────────────────────────────────────────────────

@router.get("/traffic/live")
async def get_traffic_live():
    """Return current live traffic snapshot (from in-memory sliding window)."""
    snapshot = await traffic_state.get_live_snapshot()
    return snapshot


@router.get("/traffic/history")
async def get_traffic_history(
    period: str = Query("1h", description="Time period: 15m, 1h, 6h, 24h, 7d, 30d"),
):
    """Return historical traffic aggregates from the database."""
    now = datetime.now(timezone.utc)

    period_map = {
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    delta = period_map.get(period, timedelta(hours=1))
    cutoff = now - delta

    async with async_session() as session:
        result = await session.execute(
            select(TrafficAggregate)
            .where(TrafficAggregate.timestamp >= cutoff)
            .order_by(TrafficAggregate.timestamp.asc())
        )
        rows = result.scalars().all()

    return [
        {
            "timestamp": row.timestamp.isoformat(),
            "rps": row.rps,
            "error_rate": row.error_rate,
            "active_connections": row.active_connections,
            "total_requests": row.total_requests,
            "bandwidth_bytes": row.bandwidth_bytes,
            "top_ips": row.top_ips,
            "top_endpoints": row.top_endpoints,
            "status_code_counts": row.status_code_counts,
        }
        for row in rows
    ]


# ── WebSocket endpoint ──────────────────────────────────────────────────

@router.websocket("/ws/traffic")
async def websocket_traffic(websocket: WebSocket):
    """
    WebSocket that pushes live traffic snapshots every 2 seconds.

    Accepts an optional `token` query parameter for authentication.
    """
    await websocket.accept()
    logger.info("Traffic WebSocket connected")

    try:
        while True:
            # Wait for any incoming message (or just push on interval)
            try:
                msg = await asyncio.wait_for(
                    websocket.receive_text(), timeout=2.0
                )
                # Client sent a message — could be a command, ignore for now
                if msg == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            # Push live snapshot
            snapshot = await traffic_state.get_live_snapshot()
            await websocket.send_text(json.dumps({
                "type": "traffic_snapshot",
                "data": snapshot,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))

    except WebSocketDisconnect:
        logger.info("Traffic WebSocket disconnected")
    except Exception as e:
        logger.error(f"Traffic WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass