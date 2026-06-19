"""Alert Manager FastAPI Router — CRUD rules, channels, alerts."""

import logging
from fastapi import APIRouter, HTTPException

from app.alert_manager.service import alert_manager

logger = logging.getLogger("server-stats.alert_manager.router")
router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_to_dict(a):
    return {
        "id": a.id, "rule_id": a.rule_id, "title": a.title, "message": a.message,
        "severity": a.severity, "status": a.status, "metric": a.metric,
        "current_value": a.current_value, "threshold": a.threshold, "source": a.source,
        "acknowledged_by": a.acknowledged_by, "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
        "resolved_by": a.resolved_by, "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _rule_to_dict(r):
    return {
        "id": r.id, "name": r.name, "description": r.description, "metric": r.metric,
        "condition": r.condition, "threshold": r.threshold, "severity": r.severity,
        "enabled": r.enabled, "cooldown_seconds": r.cooldown_seconds, "channel_ids": r.channel_ids,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/rules")
async def list_rules():
    return {"rules": [_rule_to_dict(r) for r in await alert_manager.get_rules()]}


@router.post("/rules")
async def create_rule(data: dict):
    rule = await alert_manager.create_rule(data)
    return _rule_to_dict(rule)


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: int):
    rule = await alert_manager.get_rule(rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, data: dict):
    rule = await alert_manager.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int):
    if not await alert_manager.delete_rule(rule_id):
        raise HTTPException(404, "Rule not found")
    return {"status": "deleted"}


@router.get("/active")
async def get_active_alerts(limit: int = 50):
    return {"alerts": [_alert_to_dict(a) for a in await alert_manager.get_active_alerts(limit)]}


@router.get("/history")
async def get_alert_history(limit: int = 100, status: str = None):
    return {"alerts": [_alert_to_dict(a) for a in await alert_manager.get_alert_history(limit, status)]}


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, data: dict):
    alert = await alert_manager.acknowledge_alert(alert_id, data.get("username", "system"))
    if not alert:
        raise HTTPException(404, "Alert not found")
    return _alert_to_dict(alert)


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, data: dict):
    alert = await alert_manager.resolve_alert(alert_id, data.get("username", "system"))
    if not alert:
        raise HTTPException(404, "Alert not found")
    return _alert_to_dict(alert)


# Channel management
@router.get("/channels")
async def list_channels():
    return {"channels": [{"id": c.id, "name": c.name, "type": c.type, "enabled": c.enabled} for c in await alert_manager.get_channels()]}


@router.post("/channels")
async def create_channel(data: dict):
    channel = await alert_manager.create_channel(data)
    return {"id": channel.id, "name": channel.name, "type": channel.type, "enabled": channel.enabled}


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int):
    if not await alert_manager.delete_channel(channel_id):
        raise HTTPException(404, "Channel not found")
    return {"status": "deleted"}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int):
    from app.models import AlertChannel
    from app.database import async_session
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(AlertChannel).where(AlertChannel.id == channel_id))
        channel = result.scalar_one_or_none()
        if not channel:
            raise HTTPException(404, "Channel not found")
        success = await alert_manager.test_channel(channel)
        return {"success": success}