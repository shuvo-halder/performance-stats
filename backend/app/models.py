"""
Unified Database Schema for Tier-1 Features.

All new tables for:
  - Alert Manager (alert_rules, alerts, alert_channels, alert_history)
  - Multi-Server (servers, server_metrics, server_status)
  - Uptime Monitor (uptime_monitors, uptime_results, uptime_incidents)
  - SSL Monitor (ssl_certificates)
  - Process Monitor (monitored_processes, process_events)
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON, Text, ForeignKey, BigInteger
from datetime import datetime, timezone
from app.database import Base


# ════════════════════════════════════════════════════════════════
# FEATURE 1: ALERT MANAGER
# ════════════════════════════════════════════════════════════════

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    metric = Column(String(100), nullable=False, index=True)  # cpu, memory, disk, load, service, malicious_ip, ssl
    condition = Column(String(20), nullable=False)             # gt, lt, eq, neq
    threshold = Column(Float, nullable=False)
    severity = Column(String(20), default="WARNING")           # INFO, WARNING, CRITICAL
    enabled = Column(Boolean, default=True)
    cooldown_seconds = Column(Integer, default=300)            # 5 min default cooldown
    channel_ids = Column(JSON, nullable=True)                  # List of alert_channel IDs
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # INFO, WARNING, CRITICAL
    status = Column(String(20), default="ACTIVE", index=True)  # ACTIVE, ACKNOWLEDGED, RESOLVED
    metric = Column(String(100), nullable=True)
    current_value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    source = Column(String(100), nullable=True)                # system, traffic, ip_reputation, ssl, uptime
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AlertChannel(Base):
    __tablename__ = "alert_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)                   # email, telegram, discord, slack, webhook
    config = Column(JSON, nullable=False)                       # {url, token, chat_id, recipients, etc}
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("alert_channels.id"), nullable=True)
    channel_type = Column(String(50), nullable=True)
    status = Column(String(20), default="SENT")                # SENT, FAILED, PENDING
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ════════════════════════════════════════════════════════════════
# FEATURE 2: MULTI-SERVER MONITORING
# ════════════════════════════════════════════════════════════════

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), nullable=False, index=True)
    public_ip = Column(String(45), nullable=True)
    private_ip = Column(String(45), nullable=True)
    os = Column(String(100), nullable=True)
    kernel = Column(String(100), nullable=True)
    agent_version = Column(String(50), nullable=True)
    agent_token = Column(String(255), nullable=False, unique=True)
    status = Column(String(20), default="OFFLINE")             # ONLINE, OFFLINE, WARNING, CRITICAL
    tags = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, nullable=True, index=True)


class ServerMetric(Base):
    __tablename__ = "server_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    cpu_percent = Column(Float)
    mem_total_mb = Column(Float)
    mem_used_mb = Column(Float)
    mem_percent = Column(Float)
    disk_data = Column(JSON)
    load_1m = Column(Float)
    load_5m = Column(Float)
    load_15m = Column(Float)
    network_connections = Column(Integer)
    top_processes = Column(JSON)
    services_data = Column(JSON)
    swap_total_mb = Column(Float, default=0)
    swap_used_mb = Column(Float, default=0)
    disk_read_iops = Column(Float, default=0)
    disk_write_iops = Column(Float, default=0)


class ServerStatus(Base):
    __tablename__ = "server_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    status = Column(String(20), default="ONLINE")
    cpu_alert = Column(Boolean, default=False)
    mem_alert = Column(Boolean, default=False)
    disk_alert = Column(Boolean, default=False)
    service_alert = Column(Boolean, default=False)
    threat_alert = Column(Boolean, default=False)
    last_metric_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ════════════════════════════════════════════════════════════════
# FEATURE 4: UPTIME MONITORING
# ════════════════════════════════════════════════════════════════

class UptimeMonitor(Base):
    __tablename__ = "uptime_monitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    monitor_type = Column(String(20), nullable=False)           # http, https, tcp, icmp
    target = Column(String(500), nullable=False)                # URL or host:port or IP
    check_interval = Column(Integer, default=60)                # seconds
    timeout = Column(Integer, default=10)                       # seconds
    retry_count = Column(Integer, default=2)
    expected_status_code = Column(Integer, default=200)
    expected_content = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_checked_at = Column(DateTime, nullable=True)
    last_status = Column(String(20), default="UNKNOWN")        # UP, DOWN, UNKNOWN
    uptime_percent = Column(Float, default=100.0)
    response_time_ms = Column(Float, nullable=True)


class UptimeResult(Base):
    __tablename__ = "uptime_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("uptime_monitors.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    status = Column(String(20), nullable=False)                 # UP, DOWN
    response_time_ms = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)


class UptimeIncident(Base):
    __tablename__ = "uptime_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("uptime_monitors.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)


# ════════════════════════════════════════════════════════════════
# FEATURE 5: SSL CERTIFICATE MONITORING
# ════════════════════════════════════════════════════════════════

class SSLCertificate(Base):
    __tablename__ = "ssl_certificates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), nullable=False, index=True)
    port = Column(Integer, default=443)
    issuer = Column(String(500), nullable=True)
    subject = Column(String(500), nullable=True)
    sans = Column(JSON, nullable=True)                          # Subject Alternative Names
    serial_number = Column(String(255), nullable=True)
    algorithm = Column(String(50), nullable=True)
    fingerprint = Column(String(255), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True, index=True)
    days_remaining = Column(Integer, nullable=True)
    status = Column(String(20), default="VALID")                # VALID, EXPIRING_SOON, EXPIRED, ERROR
    last_checked = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    error_message = Column(Text, nullable=True)


# ════════════════════════════════════════════════════════════════
# FEATURE 6: PROCESS MONITORING
# ════════════════════════════════════════════════════════════════

class MonitoredProcess(Base):
    __tablename__ = "monitored_processes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True, index=True)
    process_name = Column(String(255), nullable=False)
    service_name = Column(String(255), nullable=True)           # systemd service name
    auto_restart = Column(Boolean, default=False)
    restart_count = Column(Integer, default=0)
    max_restarts = Column(Integer, default=3)
    cpu_threshold = Column(Float, default=80.0)
    mem_threshold = Column(Float, default=80.0)
    is_running = Column(Boolean, default=True)
    cpu_percent = Column(Float, default=0.0)
    mem_percent = Column(Float, default=0.0)
    uptime_seconds = Column(BigInteger, default=0)
    last_restart_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProcessEvent(Base):
    __tablename__ = "process_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    process_id = Column(Integer, ForeignKey("monitored_processes.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)             # STARTED, STOPPED, RESTARTED, CRASHED, ALERT
    message = Column(Text, nullable=True)
    cpu_before = Column(Float, nullable=True)
    mem_before = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)