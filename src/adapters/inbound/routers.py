import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.inbound.api_schemas import (
    DispatchRequest,
    NodeRegisterRequest,
    NodeResponse,
    TaskCreateRequest,
    TaskResponse,
    TelemetryIngestRequest,
    TelemetryResponse,
    TransitionRequest,
)
from src.adapters.inbound.metrics_exporter import generate_prometheus_metrics
from src.adapters.inbound.websocket_manager import manager
from src.adapters.outbound.database import get_db_session
from src.adapters.outbound.event_publisher import LoggingEventPublisher
from src.adapters.outbound.sql_repositories import (
    SqlAsyncNodeRepository,
    SqlAsyncTaskRepository,
    SqlAsyncTelemetryRepository,
)
from src.core.domain.exceptions import (
    DuplicateNodeError,
    InvalidTaskStateException,
    InvalidTransitionTargetError,
    NodeNotFoundError,
    NodeOfflineException,
    TaskNotFoundError,
)
from src.core.use_cases.node_provisioning import NodeProvisioningService
from src.core.use_cases.task_orchestrator import TaskOrchestratorService
from src.core.use_cases.telemetry_ingestion import TelemetryIngestionService

logger = logging.getLogger(__name__)

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
    event_publisher = LoggingEventPublisher()
    return TelemetryIngestionService(node_repo, telemetry_repo, event_publisher)


# --- Node Endpoints ---


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
    try:
        node = await service.register_node(request.hostname, request.hardware_specs)
        return NodeResponse.model_validate(node)
    except DuplicateNodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


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
    try:
        await service.process_heartbeat(node_id)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.get(
    "/nodes",
    response_model=list[NodeResponse],
    summary="List all registered worker nodes",
    dependencies=[Depends(verify_api_key)]
)
async def list_nodes(
    service: NodeProvisioningService = Depends(get_node_service)
) -> list[NodeResponse]:
    nodes = await service.list_nodes()
    return [NodeResponse.model_validate(node) for node in nodes]


# --- Task Endpoints ---

@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a computational task",
    dependencies=[Depends(verify_api_key)]
)
async def create_task(
    request: TaskCreateRequest,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    task = await service.create_task(request.idempotency_key, request.payload)
    return TaskResponse.model_validate(task)


@router.post(
    "/tasks/{task_id}/dispatch",
    response_model=TaskResponse,
    summary="Dispatch task to online node",
    dependencies=[Depends(verify_api_key)]
)
async def dispatch_task(
    task_id: str,
    request: DispatchRequest,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    try:
        task = await service.dispatch_task(task_id, request.node_id)
        return TaskResponse.model_validate(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except NodeOfflineException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.post(
    "/tasks/{task_id}/transition",
    response_model=TaskResponse,
    summary="Transition running task status",
    dependencies=[Depends(verify_api_key)]
)
async def transition_task(
    task_id: str,
    request: TransitionRequest,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    try:
        task = await service.transition_task(task_id, request.target_status)
        return TaskResponse.model_validate(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except InvalidTaskStateException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except InvalidTransitionTargetError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Retrieve task details by ID",
    dependencies=[Depends(verify_api_key)]
)
async def get_task(
    task_id: str,
    service: TaskOrchestratorService = Depends(get_task_service)
) -> TaskResponse:
    try:
        task = await service.get_task(task_id)
        return TaskResponse.model_validate(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


# --- Telemetry Endpoints ---

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
    try:
        metric = await service.ingest_metrics(node_id, request.cpu_usage, request.gpu_usage, request.temperature)
        return TelemetryResponse.model_validate(metric)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc



@router.get(
    "/nodes/{node_id}/telemetry",
    response_model=list[TelemetryResponse],
    summary="Retrieve recent telemetry metrics for a worker node",
    dependencies=[Depends(verify_api_key)]
)
async def get_node_telemetry(
    node_id: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of metrics to return"),
    service: TelemetryIngestionService = Depends(get_telemetry_service)
) -> list[TelemetryResponse]:
    try:
        metrics = await service.get_latest_telemetry(node_id, limit)
        return [TelemetryResponse.model_validate(metric) for metric in metrics]
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


# --- Prometheus Metrics Endpoint ---

@router.get(
    "/metrics",
    summary="Export fleet & system metrics for Prometheus",
    dependencies=[Depends(verify_api_key)]
)
async def get_prometheus_metrics(
    session: AsyncSession = Depends(get_db_session)
) -> Response:
    metrics_text = await generate_prometheus_metrics(session)
    return Response(content=metrics_text, media_type="text/plain; version=0.0.4; charset=utf-8")



# --- WebSocket Endpoint ---

@router.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket, api_key: str = Query(..., description="Access API Key token")) -> None:
    """Accepts real-time client WebSocket connections and streams live telemetry, verifying API key token."""
    # Must accept the WebSocket before we can close it with a policy violation code
    await websocket.accept()

    if api_key != API_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connection is now authenticated — register with the manager (already accepted above)
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection open by listening for client keepalives/control messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
