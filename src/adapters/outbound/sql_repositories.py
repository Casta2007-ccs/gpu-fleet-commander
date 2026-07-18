
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.outbound.orm_models import NodeORM, TaskORM, TelemetryMetricORM
from src.core.domain.entities import Node, Task, TelemetryMetric
from src.core.ports.interfaces import INodeRepository, ITaskRepository, ITelemetryRepository


class SqlAsyncNodeRepository(INodeRepository):
    """Asynchronous PostgreSQL repository implementation for worker nodes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, node: Node) -> None:
        # Check if the node already exists for performing an upsert
        db_node = await self._session.get(NodeORM, node.id)
        if db_node is not None:
            db_node.hostname = node.hostname
            db_node.status = node.status
            db_node.hardware_specs = node.hardware_specs
            db_node.last_heartbeat = node.last_heartbeat
        else:
            db_node = NodeORM(
                id=node.id,
                hostname=node.hostname,
                status=node.status,
                hardware_specs=node.hardware_specs,
                last_heartbeat=node.last_heartbeat
            )
            self._session.add(db_node)
        await self._session.flush()  # Push changes to transaction log, let session wrapper commit

    async def find_by_id(self, node_id: str) -> Node | None:
        db_node = await self._session.get(NodeORM, node_id)
        if db_node is None:
            return None
        return Node(
            id=db_node.id,
            hostname=db_node.hostname,
            status=db_node.status,
            hardware_specs=db_node.hardware_specs,
            last_heartbeat=db_node.last_heartbeat
        )

    async def find_by_hostname(self, hostname: str) -> Node | None:
        stmt = select(NodeORM).where(NodeORM.hostname == hostname)
        result = await self._session.execute(stmt)
        db_node = result.scalar_one_or_none()
        if db_node is None:
            return None
        return Node(
            id=db_node.id,
            hostname=db_node.hostname,
            status=db_node.status,
            hardware_specs=db_node.hardware_specs,
            last_heartbeat=db_node.last_heartbeat
        )

    async def list_all(self) -> list[Node]:
        stmt = select(NodeORM)
        result = await self._session.execute(stmt)
        db_nodes = result.scalars().all()
        return [
            Node(
                id=db.id,
                hostname=db.hostname,
                status=db.status,
                hardware_specs=db.hardware_specs,
                last_heartbeat=db.last_heartbeat
            )
            for db in db_nodes
        ]


class SqlAsyncTaskRepository(ITaskRepository):
    """Asynchronous PostgreSQL repository implementation for tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save(self, task: Task) -> None:
        db_task = await self._session.get(TaskORM, task.id)
        if db_task is not None:
            db_task.payload = task.payload
            db_task.status = task.status
            db_task.retries = task.retries
            db_task.node_id = task.node_id
            db_task.completed_at = task.completed_at
        else:
            db_task = TaskORM(
                id=task.id,
                payload=task.payload,
                status=task.status,
                retries=task.retries,
                node_id=task.node_id,
                created_at=task.created_at,
                completed_at=task.completed_at,
                idempotency_key=task.idempotency_key
            )
            self._session.add(db_task)
        await self._session.flush()

    async def find_by_id(self, task_id: str) -> Task | None:
        db_task = await self._session.get(TaskORM, task_id)
        if db_task is None:
            return None
        return Task(
            id=db_task.id,
            payload=db_task.payload,
            status=db_task.status,
            idempotency_key=db_task.idempotency_key,
            retries=db_task.retries,
            node_id=db_task.node_id,
            created_at=db_task.created_at,
            completed_at=db_task.completed_at
        )

    async def find_by_idempotency_key(self, key: str) -> Task | None:
        stmt = select(TaskORM).where(TaskORM.idempotency_key == key)
        result = await self._session.execute(stmt)
        db_task = result.scalar_one_or_none()
        if db_task is None:
            return None
        return Task(
            id=db_task.id,
            payload=db_task.payload,
            status=db_task.status,
            idempotency_key=db_task.idempotency_key,
            retries=db_task.retries,
            node_id=db_task.node_id,
            created_at=db_task.created_at,
            completed_at=db_task.completed_at
        )


class SqlAsyncTelemetryRepository(ITelemetryRepository):
    """Asynchronous PostgreSQL repository implementation for telemetry metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def save_metric(self, metric: TelemetryMetric) -> None:
        db_metric = TelemetryMetricORM(
            node_id=metric.node_id,
            timestamp=metric.timestamp,
            cpu_usage=metric.cpu_usage,
            gpu_usage=metric.gpu_usage,
            temperature=metric.temperature
        )
        self._session.add(db_metric)
        await self._session.flush()

    async def get_latest_metrics_for_node(self, node_id: str, limit: int = 10) -> list[TelemetryMetric]:
        stmt = (
            select(TelemetryMetricORM)
            .where(TelemetryMetricORM.node_id == node_id)
            .order_by(TelemetryMetricORM.timestamp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        db_metrics = result.scalars().all()
        return [
            TelemetryMetric(
                node_id=db.node_id,
                timestamp=db.timestamp,
                cpu_usage=db.cpu_usage,
                gpu_usage=db.gpu_usage,
                temperature=db.temperature
            )
            for db in db_metrics
        ]
