"""
Alert Manager Service.

Handles:
  - Alert rule evaluation
  - Duplicate prevention with cooldown
  - Multi-channel notification (email, telegram, discord, slack, webhook)
  - Alert lifecycle (create, acknowledge, resolve)
"""

import asyncio
import json
import logging
import time
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import httpx
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import AlertRule, Alert, AlertChannel, AlertHistory
from app.config import settings

logger = logging.getLogger("server-stats.alert_manager")

# Track last alert time per rule to enforce cooldown
_alert_cooldowns: Dict[int, float] = {}


class AlertManager:
    """Central alert management service."""

    async def get_rules(self) -> List[AlertRule]:
        async with async_session() as session:
            result = await session.execute(
                select(AlertRule).order_by(AlertRule.created_at.desc())
            )
            return result.scalars().all()

    async def get_rule(self, rule_id: int) -> Optional[AlertRule]:
        async with async_session() as session:
            result = await session.execute(
                select(AlertRule).where(AlertRule.id == rule_id)
            )
            return result.scalar_one_or_none()

    async def create_rule(self, data: dict) -> AlertRule:
        async with async_session() as session:
            rule = AlertRule(**data)
            session.add(rule)
            await session.commit()
            await session.refresh(rule)
            return rule

    async def update_rule(self, rule_id: int, data: dict) -> Optional[AlertRule]:
        async with async_session() as session:
            result = await session.execute(
                select(AlertRule).where(AlertRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if not rule:
                return None
            for key, value in data.items():
                setattr(rule, key, value)
            rule.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(rule)
            return rule

    async def delete_rule(self, rule_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(AlertRule).where(AlertRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if not rule:
                return False
            await session.delete(rule)
            await session.commit()
            return True

    async def evaluate_rule(self, rule: AlertRule, current_value: float, source: str = "system") -> Optional[Alert]:
        """Evaluate a rule against a current value. Returns Alert if triggered."""
        now = time.time()

        # Check cooldown
        last_time = _alert_cooldowns.get(rule.id, 0)
        if now - last_time < rule.cooldown_seconds:
            return None

        # Evaluate condition
        triggered = False
        if rule.condition == "gt":
            triggered = current_value > rule.threshold
        elif rule.condition == "lt":
            triggered = current_value < rule.threshold
        elif rule.condition == "eq":
            triggered = current_value == rule.threshold
        elif rule.condition == "neq":
            triggered = current_value != rule.threshold

        if not triggered:
            return None

        # Update cooldown
        _alert_cooldowns[rule.id] = now

        # Create alert
        async with async_session() as session:
            alert = Alert(
                rule_id=rule.id,
                title=f"{rule.name} — {rule.severity}",
                message=f"Rule '{rule.name}': {rule.metric} = {current_value} (threshold: {rule.threshold})",
                severity=rule.severity,
                status="ACTIVE",
                metric=rule.metric,
                current_value=current_value,
                threshold=rule.threshold,
                source=source,
            )
            session.add(alert)
            await session.commit()
            await session.refresh(alert)

            # Send via channels
            await self._send_alert_notifications(alert, rule)

            return alert

    async def evaluate_all_rules(self, metrics: dict, source: str = "system") -> List[Alert]:
        """Evaluate all enabled rules against current metrics."""
        alerts = []
        rules = await self.get_rules()

        for rule in rules:
            if not rule.enabled:
                continue

            # Get current value for this metric
            current_value = None
            if rule.metric == "cpu" or rule.metric == "cpu_usage_percent":
                current_value = metrics.get("cpu_usage_percent", 0)
            elif rule.metric == "memory" or rule.metric == "mem_usage_percent":
                current_value = metrics.get("mem_usage_percent", 0)
            elif rule.metric == "disk" or rule.metric == "disk_usage_percent":
                # Calculate max disk usage
                disk_data = metrics.get("disk_data", [])
                current_value = max((d.get("usage_percent", 0) for d in disk_data), default=0)
            elif rule.metric == "load" or rule.metric == "cpu_load_1min":
                current_value = metrics.get("cpu_load_1min", 0)
            elif rule.metric == "service_down":
                services = metrics.get("services_data", [])
                current_value = sum(1 for s in services if "active" not in s.get("status", ""))
            elif rule.metric == "network_connections":
                current_value = metrics.get("network_connections", 0)

            if current_value is not None:
                alert = await self.evaluate_rule(rule, current_value, source)
                if alert:
                    alerts.append(alert)

        return alerts

    async def get_active_alerts(self, limit: int = 50) -> List[Alert]:
        async with async_session() as session:
            result = await session.execute(
                select(Alert)
                .where(Alert.status.in_(["ACTIVE", "ACKNOWLEDGED"]))
                .order_by(desc(Alert.created_at))
                .limit(limit)
            )
            return result.scalars().all()

    async def get_alert_history(self, limit: int = 100, status: Optional[str] = None) -> List[Alert]:
        async with async_session() as session:
            query = select(Alert).order_by(desc(Alert.created_at))
            if status:
                query = query.where(Alert.status == status)
            result = await session.execute(query.limit(limit))
            return result.scalars().all()

    async def acknowledge_alert(self, alert_id: int, username: str) -> Optional[Alert]:
        async with async_session() as session:
            result = await session.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if not alert:
                return None
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_by = username
            alert.acknowledged_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(alert)
            return alert

    async def resolve_alert(self, alert_id: int, username: str) -> Optional[Alert]:
        async with async_session() as session:
            result = await session.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if not alert:
                return None
            alert.status = "RESOLVED"
            alert.resolved_by = username
            alert.resolved_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(alert)
            return alert

    # ── Alert Channels ─────────────────────────────────────────────

    async def get_channels(self) -> List[AlertChannel]:
        async with async_session() as session:
            result = await session.execute(
                select(AlertChannel).order_by(AlertChannel.created_at.desc())
            )
            return result.scalars().all()

    async def create_channel(self, data: dict) -> AlertChannel:
        async with async_session() as session:
            channel = AlertChannel(**data)
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            return channel

    async def delete_channel(self, channel_id: int) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(AlertChannel).where(AlertChannel.id == channel_id)
            )
            channel = result.scalar_one_or_none()
            if not channel:
                return False
            await session.delete(channel)
            await session.commit()
            return True

    async def test_channel(self, channel: AlertChannel) -> bool:
        """Test a notification channel by sending a test message."""
        try:
            success = await self._send_message(channel, {
                "title": "🔔 Test Alert",
                "message": "This is a test notification from Server Stats Monitor.",
                "severity": "INFO",
            })
            return success
        except Exception as e:
            logger.error(f"Channel test failed: {e}")
            return False

    async def _send_alert_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert to all configured channels."""
        if not rule.channel_ids:
            return

        channels = await self.get_channels()
        target_channels = [c for c in channels if c.id in rule.channel_ids and c.enabled]

        for channel in target_channels:
            try:
                payload = {
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity,
                }
                success = await self._send_message(channel, payload)

                # Log to history
                async with async_session() as session:
                    history = AlertHistory(
                        alert_id=alert.id,
                        channel_id=channel.id,
                        channel_type=channel.type,
                        status="SENT" if success else "FAILED",
                    )
                    session.add(history)
                    await session.commit()
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.type}: {e}")

    async def _send_message(self, channel: AlertChannel, payload: dict) -> bool:
        """Send a message via the specified channel."""
        config = channel.config or {}

        if channel.type == "telegram":
            return await self._send_telegram(config, payload)
        elif channel.type == "discord":
            return await self._send_discord(config, payload)
        elif channel.type == "slack":
            return await self._send_slack(config, payload)
        elif channel.type == "email":
            return await self._send_email(config, payload)
        elif channel.type == "webhook":
            return await self._send_webhook(config, payload)
        return False

    async def _send_telegram(self, config: dict, payload: dict) -> bool:
        """Send alert via Telegram bot."""
        token = config.get("bot_token", settings.telegram_bot_token or "")
        chat_id = config.get("chat_id", settings.telegram_chat_id or "")
        if not token or not chat_id:
            logger.warning("Telegram not configured")
            return False

        message = f"*{payload['title']}*\n{payload['message']}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                    timeout=10,
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    async def _send_discord(self, config: dict, payload: dict) -> bool:
        """Send alert via Discord webhook."""
        url = config.get("webhook_url", "")
        if not url:
            return False

        color_map = {"INFO": 3447003, "WARNING": 15105570, "CRITICAL": 15548997}
        embed = {
            "title": payload["title"],
            "description": payload["message"],
            "color": color_map.get(payload["severity"], 3447003),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"embeds": [embed]}, timeout=10)
                return resp.status_code == 204
        except Exception as e:
            logger.error(f"Discord error: {e}")
            return False

    async def _send_slack(self, config: dict, payload: dict) -> bool:
        """Send alert via Slack webhook."""
        url = config.get("webhook_url", "")
        if not url:
            return False

        color_map = {"INFO": "#3498db", "WARNING": "#f39c12", "CRITICAL": "#e74c3c"}
        message = {
            "attachments": [{
                "color": color_map.get(payload["severity"], "#3498db"),
                "title": payload["title"],
                "text": payload["message"],
                "footer": "Server Stats Monitor",
                "ts": int(time.time()),
            }]
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=message, timeout=10)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return False

    async def _send_email(self, config: dict, payload: dict) -> bool:
        """Send alert via email."""
        import smtplib
        from email.message import EmailMessage

        recipients = config.get("recipients", [])
        smtp_host = config.get("smtp_host", settings.smtp_host or "")
        smtp_port = config.get("smtp_port", settings.smtp_port or 587)
        smtp_user = config.get("smtp_user", settings.smtp_user or "")
        smtp_pass = config.get("smtp_pass", settings.smtp_pass or "")

        if not recipients or not smtp_host:
            return False

        try:
            msg = EmailMessage()
            msg.set_content(f"{payload['title']}\n\n{payload['message']}")
            msg["Subject"] = f"[{payload['severity']}] {payload['title']}"
            msg["From"] = smtp_user
            msg["To"] = ", ".join(recipients)

            loop = asyncio.get_event_loop()

            def send():
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

            await loop.run_in_executor(None, send)
            return True
        except Exception as e:
            logger.error(f"Email error: {e}")
            return False

    async def _send_webhook(self, config: dict, payload: dict) -> bool:
        """Send alert via generic webhook."""
        url = config.get("url", "")
        headers = config.get("headers", {})
        if not url:
            return False

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={
                        "event": "alert",
                        "severity": payload["severity"],
                        "title": payload["title"],
                        "message": payload["message"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    headers=headers,
                    timeout=10,
                )
                return resp.status_code in (200, 201, 202, 204)
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False


alert_manager = AlertManager()