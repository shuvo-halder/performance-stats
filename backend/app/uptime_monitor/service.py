"""Uptime Monitor Service — HTTP/HTTPS/TCP/ICMP checks."""

import asyncio, logging, time, sys
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

    async def _perform_check(self, m) -> tuple:
        """Perform a single check against a monitor target. Returns (status, response_time_ms, status_code)."""
        start = time.time()
        status = "DOWN"
        status_code = None
        try:
            if m.monitor_type in ("http", "https"):
                import httpx
                async with httpx.AsyncClient(timeout=m.timeout, verify=False) as client:
                    resp = await client.get(m.target, follow_redirects=True)
                    status_code = resp.status_code
                    rt = (time.time() - start) * 1000
                    status = "UP" if resp.status_code == m.expected_status_code else "DOWN"
                    if m.expected_content and m.expected_content not in resp.text:
                        status = "DOWN"
            elif m.monitor_type == "tcp":
                host, port = m.target.split(":")
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, int(port)), timeout=m.timeout)
                writer.close()
                await writer.wait_closed()
                rt = (time.time() - start) * 1000
                status = "UP"
            elif m.monitor_type == "icmp":
                import subprocess
                result = subprocess.run(
                    ["ping", "-n" if sys.platform == "win32" else "-c", "1", m.target],
                    capture_output=True, timeout=m.timeout)
                rt = (time.time() - start) * 1000
                status = "UP" if result.returncode == 0 else "DOWN"
            else:
                return ("UNKNOWN", 0, None)
        except Exception:
            rt = (time.time() - start) * 1000
            status = "DOWN"
        return (status, rt, status_code)

    async def check_now(self, mid: int) -> dict:
        m = await self.get_monitor(mid)
        if not m:
            return {"error": "not found"}

        # Implement retry logic
        retries = max(1, m.retry_count or 1)
        final_status = "DOWN"
        final_rt = 0
        final_status_code = None

        for attempt in range(retries):
            status, rt, status_code = await self._perform_check(m)
            final_rt = rt
            final_status_code = status_code
            if status == "UP":
                final_status = "UP"
                break
            if attempt < retries - 1:
                await asyncio.sleep(1)  # 1 second between retries

        await self._save_result(mid, final_status, final_rt, final_status_code)
        return {"status": final_status, "response_time_ms": round(final_rt, 2)}

    async def _save_result(self, mid: int, status: str, rt: float, status_code: int = None):
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

    async def check_all_enabled(self):
        """Check all enabled monitors. Called by background scheduler."""
        monitors = await self.get_monitors()
        results = []
        for m_data in monitors:
            if not m_data.get("enabled", True):
                continue
            result = await self.check_now(m_data["id"])
            results.append({"id": m_data["id"], "name": m_data["name"], **result})
        return results


def _m_to_dict(m):
    return {
        "id": m.id, "name": m.name, "monitor_type": m.monitor_type, "target": m.target,
        "check_interval": m.check_interval, "timeout": m.timeout, "retry_count": m.retry_count,
        "expected_status_code": m.expected_status_code, "expected_content": m.expected_content,
        "enabled": m.enabled, "last_checked_at": m.last_checked_at.isoformat() if m.last_checked_at else None,
        "last_status": m.last_status, "uptime_percent": m.uptime_percent, "response_time_ms": m.response_time_ms,
    }


uptime = UptimeService()
