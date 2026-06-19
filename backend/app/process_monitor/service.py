"""Process Monitor Service — monitor, alert, auto-restart critical services."""

import asyncio, logging
from datetime import datetime, timezone
from sqlalchemy import select, desc
from app.database import async_session
from app.models import MonitoredProcess, ProcessEvent

logger = logging.getLogger("server-stats.process")


class ProcessMonitorService:
    async def create(self, data: dict) -> MonitoredProcess:
        async with async_session() as session:
            p = MonitoredProcess(**data)
            session.add(p)
            await session.commit()
            await session.refresh(p)
            return p

    async def list_all(self) -> list:
        async with async_session() as session:
            r = await session.execute(select(MonitoredProcess).order_by(MonitoredProcess.process_name))
            return [_p_dict(p) for p in r.scalars().all()]

    async def get(self, pid: int):
        async with async_session() as session:
            r = await session.execute(select(MonitoredProcess).where(MonitoredProcess.id == pid))
            return r.scalar_one_or_none()

    async def update(self, pid: int, data: dict):
        async with async_session() as session:
            r = await session.execute(select(MonitoredProcess).where(MonitoredProcess.id == pid))
            p = r.scalar_one_or_none()
            if not p: return None
            for k, v in data.items(): setattr(p, k, v)
            await session.commit()
            await session.refresh(p)
            return p

    async def delete(self, pid: int) -> bool:
        async with async_session() as session:
            r = await session.execute(select(MonitoredProcess).where(MonitoredProcess.id == pid))
            p = r.scalar_one_or_none()
            if not p: return False
            await session.delete(p)
            await session.commit()
            return True

    async def check_process(self, pid: int) -> dict:
        """Check if a monitored process is running and collect its stats."""
        import psutil
        p = await self.get(pid)
        if not p:
            return {"error": "not found"}

        found = False
        cpu = 0
        mem = 0
        uptime = 0
        name = p.process_name

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "create_time"]):
            try:
                if name.lower() in proc.info["name"].lower():
                    found = True
                    cpu = proc.info["cpu_percent"] or 0
                    mem = proc.info["memory_percent"] or 0
                    uptime = int((datetime.now().timestamp() - (proc.info["create_time"] or 0)))
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        async with async_session() as session:
            r = await session.execute(select(MonitoredProcess).where(MonitoredProcess.id == pid))
            p = r.scalar_one()
            was_running = p.is_running
            p.is_running = found
            p.cpu_percent = round(cpu, 1)
            p.mem_percent = round(mem, 1)
            p.uptime_seconds = uptime
            p.updated_at = datetime.now(timezone.utc)

            # Auto-restart logic
            if not found and p.auto_restart and p.restart_count < p.max_restarts:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "systemctl", "restart", p.service_name or p.process_name,
                        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                    await proc.wait()
                    p.restart_count += 1
                    p.last_restart_at = datetime.now(timezone.utc)
                    event = ProcessEvent(process_id=pid, event_type="RESTARTED",
                                         message=f"Auto-restarted via systemctl (attempt {p.restart_count})")
                    session.add(event)
                except Exception as e:
                    logger.error(f"Auto-restart failed for {p.process_name}: {e}")

            # Log state changes
            if was_running and not found:
                event = ProcessEvent(process_id=pid, event_type="STOPPED",
                                     message=f"Process {p.process_name} stopped")
                session.add(event)
            elif not was_running and found:
                event = ProcessEvent(process_id=pid, event_type="STARTED",
                                     message=f"Process {p.process_name} started")
                session.add(event)

            await session.commit()

        return {"id": pid, "process_name": name, "is_running": found,
                "cpu_percent": round(cpu, 1), "mem_percent": round(mem, 1),
                "uptime_seconds": uptime, "restart_count": p.restart_count}

    async def check_all(self) -> list:
        """Check all monitored processes."""
        processes = await self.list_all()
        results = []
        for p in processes:
            result = await self.check_process(p["id"])
            results.append(result)
        return results

    async def get_events(self, pid: int, limit: int = 50) -> list:
        async with async_session() as session:
            r = await session.execute(
                select(ProcessEvent).where(ProcessEvent.process_id == pid)
                .order_by(desc(ProcessEvent.created_at)).limit(limit))
            return [{"id": e.id, "event_type": e.event_type, "message": e.message,
                     "created_at": e.created_at.isoformat() if e.created_at else None}
                    for e in r.scalars().all()]


def _p_dict(p):
    return {"id": p.id, "process_name": p.process_name, "service_name": p.service_name,
            "auto_restart": p.auto_restart, "restart_count": p.restart_count,
            "max_restarts": p.max_restarts, "is_running": p.is_running,
            "cpu_percent": p.cpu_percent, "mem_percent": p.mem_percent,
            "uptime_seconds": p.uptime_seconds,
            "last_restart_at": p.last_restart_at.isoformat() if p.last_restart_at else None}


process_monitor = ProcessMonitorService()