"""Multi-Server Monitoring Service — server registration, metrics, health."""

import logging
from datetime import datetime, timezone
from typing import Optional
import secrets

from sqlalchemy import select, desc, func
from app.database import async_session
from app.models import Server, ServerMetric, ServerStatus

logger = logging.getLogger("server-stats.multi_server")


class MultiServerService:
    async def register(self, data: dict) -> Server:
        async with async_session() as session:
            token = secrets.token_hex(32)
            server = Server(
                hostname=data["hostname"],
                public_ip=data.get("public_ip"),
                private_ip=data.get("private_ip"),
                os=data.get("os"),
                kernel=data.get("kernel"),
                agent_version=data.get("agent_version", "1.0.0"),
                agent_token=token,
                status="ONLINE",
                tags=data.get("tags"),
            )
            session.add(server)
            await session.commit()
            await session.refresh(server)
            # Create status record
            status = ServerStatus(server_id=server.id)
            session.add(status)
            await session.commit()
            return server

    async def update_metrics(self, token: str, metrics: dict) -> bool:
        async with async_session() as session:
            result = await session.execute(select(Server).where(Server.agent_token == token))
            server = result.scalar_one_or_none()
            if not server:
                return False
            server.last_seen = datetime.now(timezone.utc)
            server.status = "ONLINE"

            sm = ServerMetric(server_id=server.id, **metrics)
            session.add(sm)

            # Update status
            result = await session.execute(select(ServerStatus).where(ServerStatus.server_id == server.id))
            status = result.scalar_one_or_none()
            if status:
                cpu_alert = (metrics.get("cpu_percent", 0) or 0) > 80
                mem_alert = (metrics.get("mem_percent", 0) or 0) > 85
                status.cpu_alert = cpu_alert
                status.mem_alert = mem_alert
                status.last_metric_at = datetime.now(timezone.utc)
                status.status = "WARNING" if (cpu_alert or mem_alert) else "ONLINE"

            await session.commit()
            return True

    async def list_servers(self) -> list:
        async with async_session() as session:
            result = await session.execute(select(Server).order_by(Server.hostname))
            servers = result.scalars().all()
            output = []
            for s in servers:
                status_result = await session.execute(
                    select(ServerStatus).where(ServerStatus.server_id == s.id)
                )
                status = status_result.scalar_one_or_none()
                output.append({
                    "id": s.id, "hostname": s.hostname, "public_ip": s.public_ip,
                    "private_ip": s.private_ip, "os": s.os, "kernel": s.kernel,
                    "agent_version": s.agent_version, "status": s.status,
                    "tags": s.tags, "last_seen": s.last_seen.isoformat() if s.last_seen else None,
                    "is_active": s.is_active,
                    "cpu_alert": status.cpu_alert if status else False,
                    "mem_alert": status.mem_alert if status else False,
                })
            return output

    async def get_server(self, server_id: int) -> Optional[dict]:
        async with async_session() as session:
            result = await session.execute(select(Server).where(Server.id == server_id))
            server = result.scalar_one_or_none()
            if not server:
                return None
            # Get latest metrics
            metrics_result = await session.execute(
                select(ServerMetric).where(ServerMetric.server_id == server_id)
                .order_by(desc(ServerMetric.timestamp)).limit(1)
            )
            latest = metrics_result.scalar_one_or_none()
            return {"server": {
                "id": server.id, "hostname": server.hostname, "public_ip": server.public_ip,
                "private_ip": server.private_ip, "os": server.os, "kernel": server.kernel,
                "status": server.status, "last_seen": server.last_seen.isoformat() if server.last_seen else None,
            }, "metrics": {
                "cpu_percent": latest.cpu_percent if latest else None,
                "mem_percent": latest.mem_percent if latest else None,
                "mem_total_mb": latest.mem_total_mb if latest else None,
                "mem_used_mb": latest.mem_used_mb if latest else None,
                "disk_data": latest.disk_data if latest else None,
                "load_1m": latest.load_1m if latest else None,
                "network_connections": latest.network_connections if latest else None,
            } if latest else None}

    async def get_summary(self) -> dict:
        async with async_session() as session:
            result = await session.execute(select(Server))
            servers = result.scalars().all()
            total = len(servers)
            online = sum(1 for s in servers if s.status == "ONLINE")
            offline = sum(1 for s in servers if s.status == "OFFLINE")
            warning = sum(1 for s in servers if s.status == "WARNING")
            critical = sum(1 for s in servers if s.status == "CRITICAL")
            return {"total": total, "online": online, "offline": offline, "warning": warning, "critical": critical}


multi_server = MultiServerService()