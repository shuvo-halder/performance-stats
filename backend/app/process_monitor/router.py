"""Process Monitor FastAPI Router."""

from fastapi import APIRouter, HTTPException
from app.process_monitor.service import process_monitor

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("")
async def list_processes():
    return {"processes": await process_monitor.list_all()}


@router.post("")
async def create_process(data: dict):
    p = await process_monitor.create(data)
    return {"id": p.id, "process_name": p.process_name, "service_name": p.service_name}


@router.get("/{pid}")
async def get_process(pid: int):
    p = await process_monitor.get(pid)
    if not p:
        raise HTTPException(404, "Process not found")
    from app.process_monitor.service import _p_dict
    return _p_dict(p)


@router.put("/{pid}")
async def update_process(pid: int, data: dict):
    p = await process_monitor.update(pid, data)
    if not p:
        raise HTTPException(404, "Process not found")
    from app.process_monitor.service import _p_dict
    return _p_dict(p)


@router.delete("/{pid}")
async def delete_process(pid: int):
    if not await process_monitor.delete(pid):
        raise HTTPException(404, "Process not found")
    return {"status": "deleted"}


@router.post("/{pid}/check")
async def check_process(pid: int):
    return await process_monitor.check_process(pid)


@router.post("/check-all")
async def check_all():
    return {"results": await process_monitor.check_all()}


@router.get("/{pid}/events")
async def get_events(pid: int, limit: int = 50):
    return {"events": await process_monitor.get_events(pid, limit)}