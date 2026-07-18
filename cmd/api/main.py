from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.core.domain.exceptions import (
    DomainException, NodeNotFoundError, DuplicateNodeError,
    TaskNotFoundError, NodeOfflineException, InvalidTaskStateException
)
from src.adapters.inbound.routers import router

# Initialize FastAPI application
app = FastAPI(
    title="GPU Fleet Commander API",
    description="Control Plane and Telemetry Ingestion Hub for distributed worker nodes.",
    version="1.0.0"
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
