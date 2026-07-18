import asyncio
from contextlib import asynccontextmanager
import json
import os
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from src.core.domain.exceptions import (
    DomainException, NodeNotFoundError, DuplicateNodeError,
    TaskNotFoundError, NodeOfflineException, InvalidTaskStateException
)
from src.adapters.inbound.routers import router
from src.adapters.inbound.websocket_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events, subscribing to Redis Pub/Sub if configured."""
    redis_url = os.getenv("REDIS_URL")
    listener_task = None
    
    if redis_url:
        async def listen_redis():
            client = aioredis.from_url(redis_url)
            pubsub = client.pubsub()
            await pubsub.subscribe("telemetry_channel")
            try:
                async for message in pubsub.listen():
                    if message and message["type"] == "message":
                        data = json.loads(message["data"])
                        await manager.broadcast(data)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                import logging
                logging.getLogger("lifespan").error(f"Redis Pub/Sub background listener encountered error: {e}")
            finally:
                await pubsub.close()
                await client.aclose()

        listener_task = asyncio.create_task(listen_redis())

    yield

    if listener_task:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass


# Initialize FastAPI application with lifecycle lifespan handlers
app = FastAPI(
    title="GPU Fleet Commander API",
    description="Control Plane and Telemetry Ingestion Hub for distributed worker nodes.",
    version="1.0.0",
    lifespan=lifespan
)


# --- Global Domain Exception Handlers ---

@app.exception_handler(NodeNotFoundError)
async def node_not_found_handler(request: Request, exc: NodeNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "type": "NodeNotFoundError"}
    )


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "type": "TaskNotFoundError"}
    )


@app.exception_handler(DuplicateNodeError)
async def duplicate_node_handler(request: Request, exc: DuplicateNodeError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message, "type": "DuplicateNodeError"}
    )


@app.exception_handler(NodeOfflineException)
async def node_offline_handler(request: Request, exc: NodeOfflineException) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message, "type": "NodeOfflineException"}
    )


@app.exception_handler(InvalidTaskStateException)
async def invalid_task_state_handler(request: Request, exc: InvalidTaskStateException) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message, "type": "InvalidTaskStateException"}
    )


@app.exception_handler(DomainException)
async def generic_domain_handler(request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "type": "DomainException"}
    )


# --- Register Routers ---

app.include_router(router)


# --- Root Health Check ---

@app.get("/health", status_code=200, summary="API Health Check")
async def health_check() -> dict[str, str]:
    return {"status": "ONLINE"}


# --- Serve Static Dashboard ---

@app.get("/", summary="Serve Web Dashboard")
async def serve_dashboard() -> FileResponse:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    public_index = os.path.abspath(os.path.join(current_dir, "../../public/index.html"))
    return FileResponse(public_index)
