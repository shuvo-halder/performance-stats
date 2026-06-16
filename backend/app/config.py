from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/server-stats.db"

    # Auth
    api_key: str = "sk-prod-server-stats-monitor-key-2026"
    api_key_name: str = "X-API-Key"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def services_list(self) -> List[str]:
        return [s.strip() for s in self.services.split(",") if s.strip()]


settings = Settings()