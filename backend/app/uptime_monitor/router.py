"""Uptime Monitor FastAPI Router."""

from fastapi import APIRouter, HTTPException
from app.uptime_monitor.service import uptime

router = APIRouter(prefix="/uptime", tags=["uptime"])


@router.get("/monitors")
async def list_monitors():
    return {"monitors": await uptime.get_monitors()}


@router.post("/monitors")
async def create_monitor(data: dict):
    m = await uptime.create_monitor(data)
    return {"id": m.id, "name": m.name, "target": m.target, "monitor_type": m.monitor_type}


@router.get("/monitors/{mid}")
async def get_monitor(mid: int):
    m = await uptime.get_monitor(mid)
    if not m:
        raise HTTPException(404, "Monitor not found")
    return _m_to_dict(m)


@router.put("/monitors/{mid}")
async def update_monitor(mid: int, data: dict):
    m = await uptime.update_monitor(mid, data)
    if not m:
        raise HTTPException(404, "Monitor not found")
    return _m_to_dict(m)


@router.delete("/monitors/{mid}")
async def delete_monitor(mid: int):
    if not await uptime.delete_monitor(mid):
        raise HTTPException(404, "Monitor not found")
    return {"status": "deleted"}


@router.post("/monitors/{mid}/check")
async def check_now(mid: int):
    return await uptime.check_now(mid)


@router.get("/monitors/{mid}/history")
async def get_history(mid: int, hours: int = 24):
    return {"results": await uptime.get_history(mid, hours)}


@router.get("/monitors/{mid}/incidents")
async def get_incidents(mid: int):
    return {"incidents": await uptime.get_incidents(mid)}


def _m_to_dict(m):
    return {
        "id": m.id, "name": m.name, "monitor_type": m.monitor_type, "target": m.target,
        "check_interval": m.check_interval, "timeout": m.timeout, "retry_count": m.retry_count,
        "expected_status_code": m.expected_status_code, "enabled": m.enabled,
        "last_checked_at": m.last_checked_at.isoformat() if m.last_checked_at else None,
        "last_status": m.last_status, "uptime_percent": m.uptime_percent, "response_time_ms": m.response_time_ms,
    }