from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import get_session, Snapshot
from app.collectors import collect_all_metrics
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api", tags=["Stats"])


@router.get("/stats")
async def get_current_stats(
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
):
    """Collect and return the latest system stats snapshot."""
    metrics, auto_restart_results = await collect_all_metrics()

    # Save to database (only columns that exist in Snapshot model)
    snapshot = Snapshot(**metrics, user_id=current_user.id)
    session.add(snapshot)
    await session.commit()

    # Check thresholds and build alerts
    alerts = []
    if metrics.get("cpu_usage_percent", 0) > settings.cpu_threshold:
        alerts.append({
            "type": "cpu",
            "severity": "critical",
            "message": f"High CPU usage: {metrics['cpu_usage_percent']}% (threshold: {settings.cpu_threshold}%)"
        })
    if metrics.get("mem_usage_percent", 0) > settings.mem_threshold:
        alerts.append({
            "type": "memory",
            "severity": "warning",
            "message": f"High Memory usage: {metrics['mem_usage_percent']}% (threshold: {settings.mem_threshold}%)"
        })
    for disk in metrics.get("disk_data", []):
        if disk.get("usage_percent", 0) > settings.disk_threshold:
            alerts.append({
                "type": "disk",
                "severity": "warning",
                "mount": disk["mount"],
                "message": f"High Disk usage on {disk['mount']}: {disk['usage_percent']}% (threshold: {settings.disk_threshold}%)"
            })

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": metrics.get("hostname"),
        "user": current_user.username,
        "alerts": alerts,
        **metrics,
    }


@router.get("/stats/latest")
async def get_latest_saved_stats(
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
):
    """Get the most recently saved snapshot from the database."""
    result = await session.execute(
        select(Snapshot).order_by(desc(Snapshot.timestamp)).limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No stats data available yet")
    return snapshot_to_dict(snapshot)


@router.get("/stats/history")
async def get_stats_history(
    period: str = Query("1h", description="Time period: 1h, 6h, 24h, 7d"),
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
):
    """Get historical stats snapshots."""
    now = datetime.now(timezone.utc)
    if period == "1h":
        since = now - timedelta(hours=1)
    elif period == "6h":
        since = now - timedelta(hours=6)
    elif period == "24h":
        since = now - timedelta(hours=24)
    elif period == "7d":
        since = now - timedelta(days=7)
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use 1h, 6h, 24h, or 7d")

    result = await session.execute(
        select(Snapshot)
        .where(Snapshot.timestamp >= since)
        .order_by(Snapshot.timestamp)
    )
    snapshots = result.scalars().all()
    return {
        "period": period,
        "count": len(snapshots),
        "data": [snapshot_to_dict(s) for s in snapshots],
    }


@router.get("/health")
async def health_check():
    """Health check endpoint (public, no auth required)."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/config")
async def get_config(current_user = Depends(get_current_user)):
    """View current configuration (requires auth)."""
    return {
        "cpu_threshold": settings.cpu_threshold,
        "mem_threshold": settings.mem_threshold,
        "disk_threshold": settings.disk_threshold,
        "services": settings.services_list,
        "auto_restart": settings.auto_restart_failed_services,
        "collection_interval": settings.collection_interval,
    }


def snapshot_to_dict(snapshot: Snapshot) -> dict:
    """Convert a Snapshot ORM object to a dictionary."""
    return {
        "id": snapshot.id,
        "timestamp": snapshot.timestamp.isoformat() if snapshot.timestamp else None,
        "hostname": snapshot.hostname,
        "os_name": snapshot.os_name,
        "kernel": snapshot.kernel,
        "uptime": snapshot.uptime,
        "cpu_cores": snapshot.cpu_cores,
        "cpu_usage_percent": snapshot.cpu_usage_percent,
        "cpu_load_1min": snapshot.cpu_load_1min,
        "cpu_load_5min": snapshot.cpu_load_5min,
        "cpu_load_15min": snapshot.cpu_load_15min,
        "mem_total_mb": snapshot.mem_total_mb,
        "mem_used_mb": snapshot.mem_used_mb,
        "mem_free_mb": snapshot.mem_free_mb,
        "mem_usage_percent": snapshot.mem_usage_percent,
        "disk_data": snapshot.disk_data,
        "network_connections": snapshot.network_connections,
        "network_listening_ports": snapshot.network_listening_ports,
        "failed_logins": snapshot.failed_logins,
        "services_data": snapshot.services_data,
        "top_cpu_processes": snapshot.top_cpu_processes,
        "top_mem_processes": snapshot.top_mem_processes,
    }