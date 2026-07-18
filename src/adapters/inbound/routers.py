from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.domain.entities import TaskStatus
from src.core.use_cases.node_provisioning import NodeProvisioningService
from src.core.use_cases.task_orchestrator import TaskOrchestratorService
from src.core.use_cases.telemetry_ingestion import TelemetryIngestionService
from src.adapters.outbound.database import get_db_session
from src.adapters.outbound.sql_repositories import SqlAsyncNodeRepository, SqlAsyncTaskRepository, SqlAsyncTelemetryRepository
from src.adapters.outbound.event_publisher import LoggingEventPublisher
from src.adapters.inbound.api_schemas import (
    NodeRegisterRequest, NodeResponse,
    TaskCreateRequest, TaskResponse,
    TelemetryIngestRequest, TelemetryResponse
)

router = APIRouter(prefix="/v1")


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

@router.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED, summary="Register a worker node")
async def register_node(
    request: NodeRegisterRequest,
    service: NodeProvisioningService = Depends(get_node_service)
) -> NodeResponse:
    node = await service.register_node(request.hostname, request.hardware_specs)
    return node


@router.post("/nodes/{node_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT, summary="Ingest heartbeat signal")
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


@router.post("/nodes/{node_id}/telemetry", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED, summary="Ingest node metrics telemetry")
async def ingest_telemetry(
    node_id: str,
    request: TelemetryIngestRequest,
    service: TelemetryIngestionService = Depends(get_telemetry_service)
) -> TelemetryResponse:
    metric = await service.ingest_metrics(node_id, request.cpu_usage, request.gpu_usage, request.temperature)
    return metric
