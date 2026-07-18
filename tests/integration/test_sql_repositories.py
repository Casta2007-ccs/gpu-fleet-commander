from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.outbound.database import Base
from src.adapters.outbound.sql_repositories import (
    SqlAsyncNodeRepository,
    SqlAsyncTaskRepository,
    SqlAsyncTelemetryRepository,
)
from src.core.domain.entities import Node, NodeStatus, Task, TaskStatus, TelemetryMetric


@pytest_asyncio.fixture
async def db_session():
    # Setup in-memory async SQLite database engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    # Create all tables defined in models on the test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionMaker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with AsyncSessionMaker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_node_repository_operations(db_session):
    node_repo = SqlAsyncNodeRepository(db_session)

    # Save a new node
    node = Node(
        id="node-test-123",
        hostname="gpu-node-testing",
        status=NodeStatus.ONLINE,
        hardware_specs={"gpu": "H100", "vram": 80},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(node)
    await db_session.commit()

    # Retrieve it
    db_node = await node_repo.find_by_id("node-test-123")
    assert db_node is not None
    assert db_node.hostname == "gpu-node-testing"
    assert db_node.hardware_specs == {"gpu": "H100", "vram": 80}
    assert db_node.status == NodeStatus.ONLINE

    # List all
    nodes = await node_repo.list_all()
    assert len(nodes) == 1
    assert nodes[0].id == "node-test-123"

    # Update it
    updated_node = Node(
        id="node-test-123",
        hostname="gpu-node-testing",
        status=NodeStatus.OFFLINE,
        hardware_specs={"gpu": "H100", "vram": 80},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(updated_node)
    await db_session.commit()

    db_node_updated = await node_repo.find_by_id("node-test-123")
    assert db_node_updated is not None
    assert db_node_updated.status == NodeStatus.OFFLINE


@pytest.mark.asyncio
async def test_task_repository_operations(db_session):
    node_repo = SqlAsyncNodeRepository(db_session)
    task_repo = SqlAsyncTaskRepository(db_session)

    # Foreign Key constraint requires a valid node to exist if assigned
    node = Node(
        id="node-1",
        hostname="gpu-node-testing",
        status=NodeStatus.ONLINE,
        hardware_specs={},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(node)
    await db_session.commit()

    # Save a new task (unassigned)
    task = Task(
        id="task-test-456",
        payload={"cmd": "nvidia-smi"},
        status=TaskStatus.PENDING,
        idempotency_key="idemp-12345",
        created_at=datetime.now(UTC)
    )
    await task_repo.save(task)
    await db_session.commit()

    # Retrieve by ID
    db_task = await task_repo.find_by_id("task-test-456")
    assert db_task is not None
    assert db_task.idempotency_key == "idemp-12345"
    assert db_task.node_id is None

    # Retrieve by Idempotency Key
    db_task_idemp = await task_repo.find_by_idempotency_key("idemp-12345")
    assert db_task_idemp is not None
    assert db_task_idemp.id == "task-test-456"

    # Update and assign to node
    assigned_task = Task(
        id="task-test-456",
        payload={"cmd": "nvidia-smi"},
        status=TaskStatus.RUNNING,
        idempotency_key="idemp-12345",
        node_id="node-1",
        created_at=task.created_at,
        completed_at=None
    )
    await task_repo.save(assigned_task)
    await db_session.commit()

    db_task_assigned = await task_repo.find_by_id("task-test-456")
    assert db_task_assigned is not None
    assert db_task_assigned.status == TaskStatus.RUNNING
    assert db_task_assigned.node_id == "node-1"


@pytest.mark.asyncio
async def test_telemetry_repository_operations(db_session):
    node_repo = SqlAsyncNodeRepository(db_session)
    telemetry_repo = SqlAsyncTelemetryRepository(db_session)

    node = Node(
        id="node-2",
        hostname="gpu-node-testing-2",
        status=NodeStatus.ONLINE,
        hardware_specs={},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(node)
    await db_session.commit()

    # Save a telemetry point
    now = datetime.now(UTC)
    metric = TelemetryMetric(
        node_id="node-2",
        timestamp=now,
        cpu_usage=45.2,
        gpu_usage=78.5,
        temperature=65.0
    )
    await telemetry_repo.save_metric(metric)
    await db_session.commit()

    # Retrieve latest metrics for node
    metrics = await telemetry_repo.get_latest_metrics_for_node("node-2", limit=5)
    assert len(metrics) == 1
    assert metrics[0].node_id == "node-2"
    assert metrics[0].cpu_usage == 45.2
    assert metrics[0].gpu_usage == 78.5
    assert metrics[0].temperature == 65.0
