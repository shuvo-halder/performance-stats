from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.database import init_db, async_session, Snapshot
from app.collectors import collect_all_metrics
from app.collectors.traffic import start_traffic_monitoring
from app.routers.stats import router as stats_router
from app.routers.auth import router as auth_router
from app.routers.traffic import router as traffic_router
from app.ip_reputation.router import router as ip_reputation_router
from app.ip_reputation.integration import ip_integrator
from app.metrics.router import router as metrics_router, start_background_collection, stop_background_collection
from app.agent.monitor_agent import MonitorAgent
from app.alert_manager.router import router as alert_router
from app.multi_server.router import router as servers_router
from app.uptime_monitor.router import router as uptime_router
from app.ssl_monitor.router import router as ssl_router
from app.process_monitor.router import router as process_router
from app.auth import get_current_user
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server-stats")

# Background task references
background_task = None
traffic_task = None


async def periodic_collection():
    """Periodically collect and store metrics in the background."""
    while True:
        try:
            metrics, _ = await collect_all_metrics()
            # Filter to only Snapshot-compatible fields
            snapshot_fields = {k: v for k, v in metrics.items()
                             if k in [c.name for c in Snapshot.__table__.columns]}
            async with async_session() as session:
                snapshot = Snapshot(**snapshot_fields)
                session.add(snapshot)
                await session.commit()
            logger.info(f"Background collection complete: CPU={metrics.get('cpu_usage_percent')}%, "
                        f"MEM={metrics.get('mem_usage_percent')}%")
        except Exception as e:
            logger.error(f"Background collection error: {e}")
        await asyncio.sleep(settings.collection_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Start background collection
    global background_task, traffic_task
    background_task = asyncio.create_task(periodic_collection())
    logger.info(f"Background collection started (interval: {settings.collection_interval}s)")

    # Start traffic monitoring
    traffic_task = asyncio.create_task(start_traffic_monitoring())

    # Start IP reputation enrichment
    await ip_integrator.start()
    logger.info("IP reputation enrichment started")

    # Start background metrics collection for Grafana dashboard
    await start_background_collection()
    logger.info("Background metrics collection started")

    yield

    # Shutdown
    await stop_background_collection()
    await ip_integrator.stop()
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    if traffic_task:
        traffic_task.cancel()
        try:
            await traffic_task
        except asyncio.CancelledError:
            pass
    logger.info("Server shutting down")


app = FastAPI(
    title="Server Stats Monitor API",
    version="2.0.0",
    description="Production-grade server performance monitoring API. Provides real-time and historical system metrics with user authentication.",
    lifespan=lifespan,
)

# CORS - allow configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(stats_router)
app.include_router(auth_router)
app.include_router(traffic_router)
app.include_router(ip_reputation_router)
app.include_router(metrics_router)
app.include_router(alert_router)
app.include_router(servers_router)
app.include_router(uptime_router)
app.include_router(ssl_router)
app.include_router(process_router)


# Public WebSocket routes (no auth required)
from fastapi import WebSocket
@app.websocket("/ws/metrics")
async def ws_metrics_public(websocket: WebSocket):
    await websocket.accept()
    try:
        from app.metrics.router import websocket_metrics
        await websocket_metrics(websocket)
    except Exception:
        pass

@app.websocket("/ws/traffic")
async def ws_traffic_public(websocket: WebSocket):
    await websocket.accept()
    try:
        from app.routers.traffic import websocket_traffic
        await websocket_traffic(websocket)
    except Exception:
        pass

# Agent download endpoint
from fastapi.responses import PlainTextResponse
@app.get("/api/agent/download", response_class=PlainTextResponse)
async def download_agent():
    import os
    agent_path = os.path.join(os.path.dirname(__file__), "agent", "monitor_agent.py")
    with open(agent_path, "r") as f:
        return f.read()

@app.get("/")
async def root():
    """API root with links to documentation."""
    return {
        "name": "Server Stats Monitor API",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "authentication": {
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login",
            "profile": "GET /api/auth/me",
            "create_api_key": "POST /api/auth/api-keys",
            "seed_admin": "POST /api/auth/admin/seed",
        },
    "endpoints": {
        "GET /api/stats": "Collect and return current system stats (requires auth)",
        "GET /api/stats/latest": "Get latest saved snapshot",
        "GET /api/stats/history": "Get historical stats (query: ?period=1h|6h|24h|7d)",
        "GET /api/health": "Health check (public)",
        "GET /api/config": "View current configuration",
        "GET /traffic/live": "Current live traffic snapshot (RPS, IPs, endpoints, status codes)",
        "GET /traffic/history": "Historical traffic aggregates (query: ?period=1h|6h|24h|7d)",
        "WS /ws/traffic": "WebSocket pushing live traffic every 2 seconds",
    },
    }