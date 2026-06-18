from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/server-stats.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # CORS - Frontend URL for production (set this to your dashboard URL)
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # JWT Authentication
    jwt_secret_key: str = "change-this-to-a-secure-random-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Master API Key (for automated/system access, bypasses user auth)
    # Each registered user also gets their own API key
    master_api_key: str = "sk-prod-server-stats-master-key-2026"
    api_key_name: str = "X-API-Key"

    # Thresholds
    cpu_threshold: int = 80
    mem_threshold: int = 85
    disk_threshold: int = 90

    # Services
    services: str = "nginx,docker,mysql"

    # Auto-restart
    auto_restart_failed_services: bool = True
    restart_attempts: int = 2
    restart_delay: int = 3

    # Collection
    collection_interval: int = 60

    # ── Traffic / Web Server Monitoring ──────────────────────────────────
    # Enable traffic monitoring
    traffic_monitoring_enabled: bool = True

    # Nginx log paths (comma-separated, will auto-detect if empty)
    nginx_access_log: str = "/var/log/nginx/access.log"
    nginx_error_log: str = "/var/log/nginx/error.log"

    # Apache log paths
    apache_access_log: str = "/var/log/apache2/access.log"
    apache_error_log: str = "/var/log/apache2/error.log"

    # Sliding window for live aggregation (seconds)
    traffic_window_seconds: int = 60

    # Traffic aggregation interval (seconds) — how often we flush to DB
    traffic_batch_interval: int = 5

    # Raw log retention (hours) — old raw entries are pruned
    traffic_raw_retention_hours: int = 6

    # Aggregate retention (days)
    traffic_agg_retention_days: int = 30

    # Alerts
    traffic_rps_threshold: int = 500       # Alert if RPS > this
    traffic_5xx_threshold: int = 50         # Alert if 5xx/min > this
    traffic_single_ip_threshold: int = 200  # Alert if single IP hits/min > this

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def services_list(self) -> List[str]:
        return [s.strip() for s in self.services.split(",") if s.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    @property
    def traffic_log_paths(self) -> List[str]:
        """Returns list of access log paths to tail."""
        paths = []
        for path in [self.nginx_access_log, self.apache_access_log]:
            if path and os.path.exists(path):
                paths.append(path)
        return paths


settings = Settings()