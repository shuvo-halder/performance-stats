"""Uptime Monitor Service — HTTP/HTTPS/TCP/ICMP checks."""

import asyncio, logging, time
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc
from app.database import async_session
from app.models import UptimeMonitor, UptimeResult, UptimeIncident

logger = logging.getLogger("server-stats.uptime")


class UptimeService:
    async def create_monitor(self, data: dict) -> UptimeMonitor:
        async with async_session() as session:
            m = UptimeMonitor(**data)
            session.add(m)
            await session.commit()
            await session.refresh(m)
            return m

    async def get_monitors(self) -> list:
        async with async_session() as session:
            r = await session.execute(select(UptimeMonitor).order_by(UptimeMonitor.name))
            return [_m_to_dict(x) for x in r.scalars().all()]

    async def get_monitor(self, mid: int):
        async with async_session() as session:
            r = await session.execute(select(UptimeMonitor).where(UptimeMonitor.id == mid))
            return r.scalar_one_or_none()

    async def update_monitor(self, mid: int, data: dict):
        async with async_session() as session:
            r = await session.execute(select(UptimeMonitor).where(UptimeMonitor.id == mid))
            m = r.scalar_one_or_none()
            if not m:
                return None
            for k, v in data.items():
                setattr(m, k, v)
            await session.commit()
            await session.refresh(m)
            return m

    async def delete_monitor(self, mid: int) -> bool:
        async with async_session() as session:
            r = await session.execute(select(UptimeMonitor).where(UptimeMonitor.id == mid))
            m = r.scalar_one_or_none()
            if not m:
                return False
            await session.delete(m)
            await session.commit()
            return True

    async def check_now(self, mid: int) -> dict:
        m = await self.get_monitor(mid)
        if not m:
            return {"error": "not found"}
        start = time.time()
        status = "DOWN"
        status_code = None
        try:
            if m.monitor_type in ("http", "https"):
                import httpx
                async with httpx.AsyncClient(timeout=m.timeout) as client:
                    resp = await client.get(m.target)
                    status_code = resp.status_code
                    rt = (time.time() - start) * 1000
                    status = "UP" if resp.status_code == m.expected_status_code else "DOWN"
                    if m.expected_content and m.expected_content not in resp.text:
                        status = "DOWN"
            elif m.monitor_type == "tcp":
                host, port = m.target.split(":")
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, int(port)), timeout=m.timeout)
                writer.close()
                await writer.wait_closed()
                rt = (time.time() - start) * 1000
                status = "UP"
            else:
                return {"error": "unsupported type"}
        except Exception:
            rt = (time.time() - start) * 1000
            status = "DOWN"

        async with async_session() as session:
            r = await session.execute(select(UptimeMonitor).where(UptimeMonitor.id == mid))
            mo = r.scalar_one()
            mo.last_checked_at = datetime.now(timezone.utc)
            mo.last_status = status
            mo.response_time_ms = rt

            result = UptimeResult(
                monitor_id=mid, status=status, response_time_ms=rt, status_code=status_code)
            session.add(result)

            if status == "DOWN":
                ir = await session.execute(
                    select(UptimeIncident).where(
                        UptimeIncident.monitor_id == mid, UptimeIncident.is_active == True))
                incident = ir.scalar_one_or_none()
                if not incident:
                    incident = UptimeIncident(monitor_id=mid, started_at=datetime.now(timezone.utc))
                    session.add(incident)
            else:
                ir = await session.execute(
                    select(UptimeIncident).where(
                        UptimeIncident.monitor_id == mid, UptimeIncident.is_active == True))
                for inc in ir.scalars().all():
                    inc.ended_at = datetime.now(timezone.utc)
                    inc.duration_seconds = int((inc.ended_at - inc.started_at).total_seconds())
                    inc.is_active = False

            # Calculate 24h uptime %
            one_day = datetime.now(timezone.utc) - timedelta(hours=24)
            hr = await session.execute(
                select(UptimeResult).where(
                    UptimeResult.monitor_id == mid, UptimeResult.timestamp >= one_day))
            results = hr.scalars().all()
            up = sum(1 for r in results if r.status == "UP")
            mo.uptime_percent = round((up / len(results)) * 100, 2) if results else 100.0
            await session.commit()

        return {"status": status, "response_time_ms": round(rt, 2), "uptime_percent": mo.uptime_percent}

    async def get_history(self, mid: int, hours: int = 24) -> list:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        async with async_session() as session:
            r = await session.execute(
                select(UptimeResult).where(
                    UptimeResult.monitor_id == mid, UptimeResult.timestamp >= since)
                .order_by(UptimeResult.timestamp.desc()).limit(500))
            return [{"timestamp": x.timestamp.isoformat(), "status": x.status,
                     "response_time_ms": x.response_time_ms} for x in r.scalars().all()]

    async def get_incidents(self, mid: int) -> list:
        async with async_session() as session:
            r = await session.execute(
                select(UptimeIncident).where(UptimeIncident.monitor_id == mid)
                .order_by(desc(UptimeIncident.started_at)).limit(50))
            return [{"id": x.id, "started_at": x.started_at.isoformat(),
                     "ended_at": x.ended_at.isoformat() if x.ended_at else None,
                     "duration": x.duration_seconds, "is_active": x.is_active}
                    for x in r.scalars().all()]


def _m_to_dict(m):
    return {
        "id": m.id, "name": m.name, "monitor_type": m.monitor_type, "target": m.target,
        "check_interval": m.check_interval, "timeout": m.timeout, "retry_count": m.retry_count,
        "expected_status_code": m.expected_status_code, "expected_content": m.expected_content,
        "enabled": m.enabled, "last_checked_at": m.last_checked_at.isoformat() if m.last_checked_at else None,
        "last_status": m.last_status, "uptime_percent": m.uptime_percent, "response_time_ms": m.response_time_ms,
    }


uptime = UptimeService()