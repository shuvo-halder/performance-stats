from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON
from datetime import datetime, timezone
import os

from app.config import settings

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # CPU
    cpu_cores = Column(Integer)
    cpu_usage_percent = Column(Float)
    cpu_load_1min = Column(Float)
    cpu_load_5min = Column(Float)
    cpu_load_15min = Column(Float)

    # Memory
    mem_total_mb = Column(Float)
    mem_used_mb = Column(Float)
    mem_free_mb = Column(Float)
    mem_usage_percent = Column(Float)

    # Disk (JSON array of mount points)
    disk_data = Column(JSON)

    # Network
    network_connections = Column(Integer)
    network_listening_ports = Column(JSON)

    # Security
    failed_logins = Column(Integer, default=0)

    # Services (JSON)
    services_data = Column(JSON)

    # Top processes (JSON)
    top_cpu_processes = Column(JSON)
    top_mem_processes = Column(JSON)

    # System info
    hostname = Column(String(255))
    os_name = Column(String(255))
    kernel = Column(String(255))
    uptime = Column(String(255))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session