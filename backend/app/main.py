from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.database import init_db, async_session, Snapshot
from app.collectors import collect_all_metrics
from app.routers.stats import router as stats_router
from app.routers.auth import router as auth_router
from app.auth import get_current_user
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server-stats")

# Background task reference
background_task = None


async def periodic_collection():
    """Periodically collect and store metrics in the background."""
    while True:
        try:
            metrics, _ = await collect_all_metrics()
            async with async_session() as session:
                snapshot = Snapshot(**metrics)
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
    global background_task
    background_task = asyncio.create_task(periodic_collection())
    logger.info(f"Background collection started (interval: {settings.collection_interval}s)")

    yield

    # Shutdown
    if background_task:
        background_task.cancel()
        try:
            await background_task
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
        },
    }