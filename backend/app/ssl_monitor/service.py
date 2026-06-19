"""SSL Certificate Monitor Service — fetches and scans SSL certs."""

import asyncio, logging, ssl, socket
from datetime import datetime, timezone
from sqlalchemy import select, desc
from app.database import async_session
from app.models import SSLCertificate

logger = logging.getLogger("server-stats.ssl")


class SSLMonitorService:
    async def scan(self, hostname: str, port: int = 443) -> dict:
        """Fetch SSL certificate for a hostname and store it."""
        try:
            ctx = ssl.create_default_context()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port, ssl=ctx), timeout=10)
            cert = writer.get_extra_info("peercert")
            writer.close()
            await writer.wait_closed()

            valid_from = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
            valid_to = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
            days_remaining = (valid_to - datetime.now()).days
            sans = cert.get("subjectAltName", [])
            sans_list = [s[1] for s in sans] if sans else []

            if days_remaining <= 3:
                status = "EXPIRING_SOON"
            elif days_remaining <= 7:
                status = "EXPIRING_SOON"
            elif days_remaining <= 15:
                status = "EXPIRING_SOON"
            elif days_remaining <= 30:
                status = "EXPIRING_SOON"
            elif days_remaining <= 0:
                status = "EXPIRED"
            else:
                status = "VALID"

            async with async_session() as session:
                r = await session.execute(
                    select(SSLCertificate).where(
                        SSLCertificate.hostname == hostname, SSLCertificate.port == port))
                existing = r.scalar_one_or_none()

                data = {
                    "issuer": str(cert.get("issuer")),
                    "subject": str(cert.get("subject")),
                    "sans": sans_list,
                    "serial_number": str(cert.get("serialNumber")),
                    "algorithm": cert.get("signatureAlgorithm", ""),
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                    "days_remaining": days_remaining,
                    "status": status,
                    "last_checked": datetime.now(timezone.utc),
                    "error_message": None,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    existing = SSLCertificate(hostname=hostname, port=port, **data)
                    session.add(existing)
                await session.commit()
                await session.refresh(existing)

            return {
                "hostname": hostname, "port": port, "issuer": str(cert.get("issuer")),
                "valid_from": valid_from.isoformat(), "valid_to": valid_to.isoformat(),
                "days_remaining": days_remaining, "status": status, "sans": sans_list,
            }
        except Exception as e:
            logger.error(f"SSL scan error for {hostname}:{port}: {e}")
            # Store error state
            async with async_session() as session:
                r = await session.execute(
                    select(SSLCertificate).where(
                        SSLCertificate.hostname == hostname, SSLCertificate.port == port))
                existing = r.scalar_one_or_none()
                if not existing:
                    existing = SSLCertificate(hostname=hostname, port=port)
                    session.add(existing)
                existing.status = "ERROR"
                existing.error_message = str(e)
                existing.last_checked = datetime.now(timezone.utc)
                await session.commit()
            return {"hostname": hostname, "port": port, "status": "ERROR", "error": str(e)}

    async def list_certificates(self) -> list:
        async with async_session() as session:
            r = await session.execute(
                select(SSLCertificate).order_by(desc(SSLCertificate.last_checked)))
            return [{"id": c.id, "hostname": c.hostname, "port": c.port,
                     "issuer": c.issuer, "valid_to": c.valid_to.isoformat() if c.valid_to else None,
                     "days_remaining": c.days_remaining, "status": c.status,
                     "last_checked": c.last_checked.isoformat() if c.last_checked else None}
                    for c in r.scalars().all()]

    async def get_certificate(self, cert_id: int) -> dict:
        async with async_session() as session:
            r = await session.execute(select(SSLCertificate).where(SSLCertificate.id == cert_id))
            c = r.scalar_one_or_none()
            if not c:
                return None
            return {"id": c.id, "hostname": c.hostname, "port": c.port,
                    "issuer": c.issuer, "subject": c.subject, "sans": c.sans,
                    "serial_number": c.serial_number, "algorithm": c.algorithm,
                    "valid_from": c.valid_from.isoformat() if c.valid_from else None,
                    "valid_to": c.valid_to.isoformat() if c.valid_to else None,
                    "days_remaining": c.days_remaining, "status": c.status,
                    "last_checked": c.last_checked.isoformat() if c.last_checked else None,
                    "error_message": c.error_message}


ssl_monitor = SSLMonitorService()