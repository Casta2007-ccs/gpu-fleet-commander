from datetime import UTC, datetime

import pytest

from src.core.domain.entities import Node, NodeStatus, TaskStatus
from src.core.domain.exceptions import (
    InvalidTaskStateException,
    InvalidTransitionTargetError,
    NodeNotFoundError,
    NodeOfflineException,
    TaskNotFoundError,
)
from src.core.use_cases.task_orchestrator import TaskOrchestratorService
from tests.unit.fakes import FakeEventPublisher, FakeNodeRepository, FakeTaskRepository


@pytest.fixture
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture
def node_repo() -> FakeNodeRepository:
    return FakeNodeRepository()


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def service(
    task_repo: FakeTaskRepository,
    node_repo: FakeNodeRepository,
    event_publisher: FakeEventPublisher
) -> TaskOrchestratorService:
    return TaskOrchestratorService(task_repo, node_repo, event_publisher)


@pytest.mark.asyncio
async def test_create_task_success(service: TaskOrchestratorService, task_repo: FakeTaskRepository):
    idempotency_key = "idemp-key-123"
    payload = {"command": "run-benchmark", "gpu_id": 0}

    task = await service.create_task(idempotency_key, payload)

    assert task.id is not None
    assert task.idempotency_key == idempotency_key
    assert task.payload == payload
    assert task.status == TaskStatus.PENDING

    # Check persistence
    db_task = await task_repo.find_by_id(task.id)
    assert db_task is not None
    assert db_task.idempotency_key == idempotency_key


@pytest.mark.asyncio
async def test_create_task_idempotency_returns_existing_task(service: TaskOrchestratorService, task_repo: FakeTaskRepository):
    idempotency_key = "idemp-key-123"
    payload1 = {"command": "run-benchmark"}
    payload2 = {"command": "run-another"}

    task1 = await service.create_task(idempotency_key, payload1)
    task2 = await service.create_task(idempotency_key, payload2)

    assert task1.id == task2.id
    assert task2.payload == payload1


@pytest.mark.asyncio
async def test_dispatch_task_success(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository,
    node_repo: FakeNodeRepository,
    event_publisher: FakeEventPublisher
):
    # Setup node
    node = Node(
        id="node-1",
        hostname="nv-host-01",
        status=NodeStatus.ONLINE,
        hardware_specs={},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(node)

    # Setup task
    task = await service.create_task("key-1", {"job": "compile"})

    # Dispatch
    dispatched_task = await service.dispatch_task(task.id, node.id)

    assert dispatched_task.status == TaskStatus.RUNNING
    assert dispatched_task.node_id == node.id

    # Check event published
    assert len(event_publisher.events) == 1
    assert event_publisher.events[0]["type"] == "task_dispatched"
    assert event_publisher.events[0]["data"].id == task.id


@pytest.mark.asyncio
async def test_dispatch_task_node_offline_raises_error(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository,
    node_repo: FakeNodeRepository
):
    # Setup offline node
    node = Node(
        id="node-1",
        hostname="nv-host-01",
        status=NodeStatus.OFFLINE,
        hardware_specs={},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(node)

    # Setup task
    task = await service.create_task("key-1", {"job": "compile"})

    with pytest.raises(NodeOfflineException):
        await service.dispatch_task(task.id, node.id)


@pytest.mark.asyncio
async def test_dispatch_task_not_found_raises_error(service: TaskOrchestratorService):
    with pytest.raises(TaskNotFoundError):
        await service.dispatch_task("invalid-task-id", "any-node")


@pytest.mark.asyncio
async def test_dispatch_task_node_not_found_raises_error(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository
):
    task = await service.create_task("key-1", {"job": "compile"})
    with pytest.raises(NodeNotFoundError):
        await service.dispatch_task(task.id, "invalid-node-id")


@pytest.mark.asyncio
async def test_transition_task_completed_success(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository,
    node_repo: FakeNodeRepository,
    event_publisher: FakeEventPublisher
):
    # Setup node and running task
    node = Node("node-1", "nv-host-01", NodeStatus.ONLINE, {}, datetime.now(UTC))
    await node_repo.save(node)
    task = await service.create_task("key-1", {"job": "compile"})
    await service.dispatch_task(task.id, node.id)

    # Transition to completed
    completed_task = await service.transition_task(task.id, TaskStatus.COMPLETED)

    assert completed_task.status == TaskStatus.COMPLETED
    assert isinstance(completed_task.completed_at, datetime)

    # Check event
    assert event_publisher.events[-1]["type"] == "task_status_changed"
    assert event_publisher.events[-1]["data"].status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_transition_task_failed_success(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository,
    node_repo: FakeNodeRepository,
    event_publisher: FakeEventPublisher
):
    node = Node("node-1", "nv-host-01", NodeStatus.ONLINE, {}, datetime.now(UTC))
    await node_repo.save(node)
    task = await service.create_task("key-1", {"job": "compile"})
    await service.dispatch_task(task.id, node.id)

    # Transition to failed
    failed_task = await service.transition_task(task.id, TaskStatus.FAILED)

    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.retries == 1
    assert isinstance(failed_task.completed_at, datetime)


@pytest.mark.asyncio
async def test_transition_invalid_state_raises_error(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository
):
    task = await service.create_task("key-1", {"job": "compile"})

    with pytest.raises(InvalidTaskStateException):
        await service.transition_task(task.id, TaskStatus.COMPLETED)


@pytest.mark.asyncio
async def test_transition_invalid_target_status_raises_error(
    service: TaskOrchestratorService,
    task_repo: FakeTaskRepository,
    node_repo: FakeNodeRepository
):
    node = Node("node-1", "nv-host-01", NodeStatus.ONLINE, {}, datetime.now(UTC))
    await node_repo.save(node)
    task = await service.create_task("key-1", {"job": "compile"})
    await service.dispatch_task(task.id, node.id)

    with pytest.raises(InvalidTransitionTargetError):
        await service.transition_task(task.id, TaskStatus.RUNNING)


@pytest.mark.asyncio
async def test_get_task_success(service: TaskOrchestratorService):
    created = await service.create_task("key-10", {"cmd": "test"})
    retrieved = await service.get_task(created.id)
    assert retrieved.id == created.id
    assert retrieved.idempotency_key == "key-10"


@pytest.mark.asyncio
async def test_get_task_not_found_raises_error(service: TaskOrchestratorService):
    with pytest.raises(TaskNotFoundError):
        await service.get_task("non-existent-task-id")


