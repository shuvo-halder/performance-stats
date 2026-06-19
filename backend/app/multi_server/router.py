"""Multi-Server FastAPI Router."""

import logging
from fastapi import APIRouter, HTTPException, Request
from app.multi_server.service import multi_server

logger = logging.getLogger("server-stats.multi_server.router")
router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/summary")
async def get_summary():
    return await multi_server.get_summary()


@router.get("")
async def list_servers():
    return {"servers": await multi_server.list_servers()}


@router.post("/register")
async def register_server(data: dict):
    server = await multi_server.register(data)
    return {"id": server.id, "token": server.agent_token, "hostname": server.hostname}


@router.post("/metrics")
async def update_metrics(request: Request, data: dict):
    # Agent sends token in X-Agent-Token header, fallback to query param
    token = request.headers.get("X-Agent-Token") or request.query_params.get("token", "")
    if not token or not await multi_server.update_metrics(token, data):
        raise HTTPException(401, "Invalid agent token")
    return {"status": "ok"}


@router.get("/{server_id}")
async def get_server(server_id: int):
    result = await multi_server.get_server(server_id)
    if not result:
        raise HTTPException(404, "Server not found")
    return result


@router.delete("/{server_id}")
async def delete_server(server_id: int):
    if not await multi_server.delete_server(server_id):
        raise HTTPException(404, "Server not found")
    return {"status": "deleted"}
