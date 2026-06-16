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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def services_list(self) -> List[str]:
        return [s.strip() for s in self.services.split(",") if s.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]


settings = Settings()