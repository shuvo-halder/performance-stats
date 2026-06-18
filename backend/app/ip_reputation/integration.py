"""
Integration layer between IP Reputation and Traffic Monitoring.

Provides:
  - Real-time IP enrichment during traffic processing
  - Alert generation for malicious/suspicious IPs
  - Reputation data attached to live traffic snapshots
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.config import settings
from app.collectors.traffic import traffic_state
from app.ip_reputation.service import ip_reputation_service

logger = logging.getLogger("server-stats.ip-reputation.integration")


class IPReputationIntegrator:
    """
    Integrates IP reputation data into the traffic monitoring pipeline.
    Runs as a background task that periodically enriches top IPs with reputation data.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        # Track IPs we've already checked to avoid redundant lookups
        self._checked_ips: set = set()
        # Track IP request counts for alerting
        self._ip_request_counts: Dict[str, int] = {}
        # Alert cooldown tracking
        self._last_alert_time: Dict[str, float] = {}

    async def enrich_top_ips(self):
        """
        Enrich the top IPs from traffic state with reputation data.
        This is called periodically from the background task.
        """
        if not settings.ip_reputation_enabled:
            return

        try:
            # Get current live snapshot to find top IPs
            snapshot = await traffic_state.get_live_snapshot()
            top_ips = snapshot.get("top_ips", [])

            if not top_ips:
                return

            # Extract unique IPs
            ips_to_check = [item["ip"] for item in top_ips]

            # Batch check reputation for all top IPs
            if ips_to_check:
                results = await ip_reputation_service.batch_check(ips_to_check)

                # Mark checked IPs
                for ip in ips_to_check:
                    self._checked_ips.add(ip)

                # Check for alerts
                await self._check_alerts(results, top_ips)

                return results

        except Exception as e:
            logger.error(f"Error enriching top IPs: {e}")

        return None

    async def _check_alerts(self, reputation_results: Dict[str, dict], top_ips: List[dict]):
        """Generate alerts for malicious/suspicious IPs."""
        import time

        alerts = []
        now = time.time()
        cooldown = 60  # seconds between same alert type

        for item in top_ips:
            ip = item["ip"]
            count = item.get("count", 0)
            rep = reputation_results.get(ip)

            if not rep:
                continue

            abuse_score = rep.get("abuse_score", 0)
            is_malicious = rep.get("is_malicious", False)
            threat_flags = rep.get("threat_flags", [])

            # Alert 1: High abuse score
            if abuse_score >= settings.ip_reputation_abuse_threshold:
                key = f"abuse_{ip}"
                if now - self._last_alert_time.get(key, 0) > cooldown:
                    alerts.append({
                        "type": "malicious_ip",
                        "severity": "critical",
                        "message": f"Malicious IP detected: {ip} (abuse score: {abuse_score})",
                        "ip": ip,
                        "abuse_score": abuse_score,
                    })
                    self._last_alert_time[key] = now

            # Alert 2: High request count from suspicious IP
            if count > settings.ip_reputation_max_requests_per_ip and abuse_score > 30:
                key = f"high_rps_{ip}"
                if now - self._last_alert_time.get(key, 0) > cooldown:
                    alerts.append({
                        "type": "ip_flood_suspicious",
                        "severity": "warning",
                        "message": f"Suspicious IP flood: {ip} — {count} requests (abuse: {abuse_score})",
                        "ip": ip,
                        "count": count,
                        "abuse_score": abuse_score,
                    })
                    self._last_alert_time[key] = now

            # Alert 3: Bot/Proxy flagged with high RPS
            is_bot_or_proxy = any(f in threat_flags for f in ["proxy", "vpn", "bot"])
            if is_bot_or_proxy and count > 100:
                key = f"bot_proxy_{ip}"
                if now - self._last_alert_time.get(key, 0) > cooldown:
                    alerts.append({
                        "type": "bot_proxy_detected",
                        "severity": "warning",
                        "message": f"Bot/Proxy IP: {ip} — flags: {', '.join(threat_flags)} ({count} requests)",
                        "ip": ip,
                        "threat_flags": threat_flags,
                        "count": count,
                    })
                    self._last_alert_time[key] = now

        # Push alerts to traffic state
        for alert in alerts:
            await traffic_state._add_alert(alert)

        if alerts:
            logger.warning(f"Generated {len(alerts)} IP reputation alerts")

    async def get_enriched_snapshot(self) -> dict:
        """
        Get a live traffic snapshot with reputation data attached to top IPs.
        """
        snapshot = await traffic_state.get_live_snapshot()

        if not settings.ip_reputation_enabled:
            return snapshot

        # Enrich top IPs with reputation status
        enriched_ips = []
        for item in snapshot.get("top_ips", []):
            ip = item["ip"]
            rep = await ip_reputation_service.check_ip(ip)
            enriched_ips.append({
                **item,
                "abuse_score": rep.get("abuse_score", 0),
                "country": rep.get("country"),
                "is_malicious": rep.get("is_malicious", False),
                "threat_flags": rep.get("threat_flags", []),
                "status": self._get_status_label(rep),
            })

        snapshot["top_ips"] = enriched_ips

        # Add threat summary
        malicious_count = sum(1 for ip in enriched_ips if ip.get("is_malicious"))
        suspicious_count = sum(1 for ip in enriched_ips if ip.get("abuse_score", 0) >= 30 and not ip.get("is_malicious"))
        snapshot["threat_summary"] = {
            "total_ips": len(enriched_ips),
            "malicious": malicious_count,
            "suspicious": suspicious_count,
            "safe": len(enriched_ips) - malicious_count - suspicious_count,
        }

        return snapshot

    def _get_status_label(self, rep: dict) -> str:
        """Return SAFE, SUSPICIOUS, or MALICIOUS."""
        score = rep.get("abuse_score", 0)
        if score >= 70:
            return "MALICIOUS"
        elif score >= 30:
            return "SUSPICIOUS"
        return "SAFE"

    async def start(self):
        """Start the background enrichment loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._enrichment_loop())
        logger.info("IP reputation enrichment loop started")

    async def stop(self):
        """Stop the background enrichment loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await ip_reputation_service.close()
        logger.info("IP reputation enrichment loop stopped")

    async def _enrichment_loop(self):
        """Background loop that enriches top IPs every 30 seconds."""
        while self._running:
            try:
                await self.enrich_top_ips()
            except Exception as e:
                logger.error(f"IP enrichment loop error: {e}")
            await asyncio.sleep(30)


# ── Global integrator singleton ─────────────────────────────────────────

ip_integrator = IPReputationIntegrator()