import os
from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.domain.entities import TaskStatus
from src.core.use_cases.node_provisioning import NodeProvisioningService
from src.core.use_cases.task_orchestrator import TaskOrchestratorService
from src.core.use_cases.telemetry_ingestion import TelemetryIngestionService
from src.adapters.outbound.database import get_db_session
from src.adapters.outbound.sql_repositories import SqlAsyncNodeRepository, SqlAsyncTaskRepository, SqlAsyncTelemetryRepository
from src.adapters.outbound.event_publisher import LoggingEventPublisher
from src.adapters.inbound.websocket_manager import manager
from src.adapters.inbound.api_schemas import (
    NodeRegisterRequest, NodeResponse,
    TaskCreateRequest, TaskResponse,
    TelemetryIngestRequest, TelemetryResponse
)

router = APIRouter(prefix="/v1")

# Global API Key configuration (configured via environment or pre-shared default token)
API_KEY = os.getenv("API_KEY", "gpu_fleet_secure_token_2026")


# --- Security Verification Dependencies ---

async def verify_api_key(x_api_key: str = Header(..., description="Access API Key for control plane authentication")) -> None:
    """Verifies that the incoming client HTTP request contains a valid X-API-Key header."""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header credential"
        )


# --- Dependency Injection Helpers (Request Scoped) ---

async def get_node_service(session: AsyncSession = Depends(get_db_session)) -> NodeProvisioningService:
    node_repo = SqlAsyncNodeRepository(session)
    event_publisher = LoggingEventPublisher()
    return NodeProvisioningService(node_repo, event_publisher)


async def get_task_service(session: AsyncSession = Depends(get_db_session)) -> TaskOrchestratorService:
    task_repo = SqlAsyncTaskRepository(session)
    node_repo = SqlAsyncNodeRepository(session)
    event_publisher = LoggingEventPublisher()
    return TaskOrchestratorService(task_repo, node_repo, event_publisher)


async def get_telemetry_service(session: AsyncSession = Depends(get_db_session)) -> TelemetryIngestionService:
    node_repo = SqlAsyncNodeRepository(session)
    telemetry_repo = SqlAsyncTelemetryRepository(session)
    return TelemetryIngestionService(node_repo, telemetry_repo)


# --- Endpoints ---

@router.post(
    "/nodes", 
    response_model=NodeResponse, 
    status_code=status.HTTP_201_CREATED, 
    summary="Register a worker node",
    dependencies=[Depends(verify_api_key)]
)
async def register_node(
    request: NodeRegisterRequest,
    service: NodeProvisioningService = Depends(get_node_service)
) -> NodeResponse:
    node = await service.register_node(request.hostname, request.hardware_specs)
    return node


@router.post(
    "/nodes/{node_id}/heartbeat", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Ingest heartbeat signal",
    dependencies=[Depends(verify_api_key)]
)
async def process_heartbeat(
    node_id: str,
    service: NodeProvisioningService = Depends(get_node_service)
) -> None:
    await service.process_heartbeat(node_id)


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Create a computational task")
async def create_task(
    request: TaskCreateRequest,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    task = await service.create_task(request.idempotency_key, request.payload)
    return task


@router.post("/tasks/{task_id}/dispatch", response_model=TaskResponse, summary="Dispatch task to online node")
async def dispatch_task(
    task_id: str,
    node_id: str,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    task = await service.dispatch_task(task_id, node_id)
    return task


@router.post("/tasks/{task_id}/transition", response_model=TaskResponse, summary="Transition running task status")
async def transition_task(
    task_id: str,
    target_status: TaskStatus,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    task = await service.transition_task(task_id, target_status)
    return task


@router.post(
    "/nodes/{node_id}/telemetry", 
    response_model=TelemetryResponse, 
    status_code=status.HTTP_201_CREATED, 
    summary="Ingest node metrics telemetry",
    dependencies=[Depends(verify_api_key)]
)
async def ingest_telemetry(
    node_id: str,
    request: TelemetryIngestRequest,
    service: TelemetryIngestionService = Depends(get_telemetry_service)
) -> TelemetryResponse:
    metric = await service.ingest_metrics(node_id, request.cpu_usage, request.gpu_usage, request.temperature)
    
    # Broadcast telemetry points (via Redis Pub/Sub if active, otherwise local in-memory fallback)
    await manager.publish_telemetry({
        "node_id": metric.node_id,
        "timestamp": metric.timestamp.isoformat(),
        "cpu_usage": metric.cpu_usage,
        "gpu_usage": metric.gpu_usage,
        "temperature": metric.temperature
    })
    
    return metric


@router.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket, api_key: str = Query(..., description="Access API Key token")) -> None:
    """Accepts real-time client WebSocket connections and streams live telemetry, verifying API key token."""
    if api_key != API_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection open by listening for client keepalives/control messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
