"""
FastAPI Router for IP Reputation and Threat Intelligence.

Endpoints:
  GET /ip/{ip}           — full reputation data for a single IP
  GET /ip/top-malicious  — highest risk IPs from recent traffic
  GET /ip/stats          — summary statistics
  GET /ip/check/{ip}     — force re-check an IP (bypass cache)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.auth import get_current_user_optional
from app.ip_reputation.service import ip_reputation_service
from app.ip_reputation.models import IPReputation

logger = logging.getLogger("server-stats.ip-reputation.router")

router = APIRouter(prefix="/ip", tags=["ip-reputation"])


@router.get("/{ip}")
async def get_ip_reputation(ip: str):
    """
    Get full IP reputation data.
    If not in cache, queries external providers.
    """
    try:
        result = await ip_reputation_service.check_ip(ip)
        return result
    except Exception as e:
        logger.error(f"Error checking IP {ip}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check IP reputation: {str(e)}")


@router.get("/check/{ip}")
async def force_check_ip(ip: str):
    """
    Force re-check an IP address, bypassing cache.
    """
    try:
        # Clear from in-memory cache
        await ip_reputation_service.cache.clear()
        result = await ip_reputation_service.check_ip(ip)
        return result
    except Exception as e:
        logger.error(f"Error force-checking IP {ip}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check IP reputation: {str(e)}")


@router.get("/top-malicious")
async def get_top_malicious(
    limit: int = Query(20, description="Number of results to return"),
):
    """Get highest risk IPs from the database."""
    try:
        results = await ip_reputation_service.get_top_malicious(limit=limit)
        return {"top_malicious_ips": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting top malicious IPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_ip_stats():
    """Get summary statistics about IP reputation data."""
    try:
        stats = await ip_reputation_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting IP reputation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-check")
async def batch_check_ips(ips: list[str]):
    """
    Check multiple IPs and return results.
    Accepts a JSON body: {"ips": ["1.2.3.4", "5.6.7.8"]}
    """
    if not ips:
        raise HTTPException(status_code=400, detail="No IPs provided")
    if len(ips) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 IPs per batch request")

    try:
        results = await ip_reputation_service.batch_check(ips)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in batch IP check: {e}")
        raise HTTPException(status_code=500, detail=str(e))