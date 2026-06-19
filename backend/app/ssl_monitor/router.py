"""SSL Certificate Monitor FastAPI Router."""

from fastapi import APIRouter, HTTPException
from app.ssl_monitor.service import ssl_monitor

router = APIRouter(prefix="/ssl", tags=["ssl"])


@router.post("/scan")
async def scan_certificate(data: dict):
    hostname = data.get("hostname", "")
    port = data.get("port", 443)
    if not hostname:
        raise HTTPException(400, "hostname required")
    return await ssl_monitor.scan(hostname, port)


@router.get("/certificates")
async def list_certificates():
    return {"certificates": await ssl_monitor.list_certificates()}


@router.get("/certificates/{cert_id}")
async def get_certificate(cert_id: int):
    cert = await ssl_monitor.get_certificate(cert_id)
    if not cert:
        raise HTTPException(404, "Certificate not found")
    return cert