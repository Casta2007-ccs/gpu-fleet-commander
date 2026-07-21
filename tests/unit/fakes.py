from typing import Any

from src.core.domain.entities import Node, Task, TelemetryMetric
from src.core.ports.interfaces import IEventPublisher, INodeRepository, ITaskRepository, ITelemetryRepository


class FakeNodeRepository(INodeRepository):
    """In-memory node repository for unit tests."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    async def save(self, node: Node) -> None:
        self.nodes[node.id] = node

    async def find_by_id(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    async def find_by_id_for_update(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    async def find_by_hostname(self, hostname: str) -> Node | None:
        for node in self.nodes.values():
            if node.hostname == hostname:
                return node
        return None

    async def list_all(self) -> list[Node]:
        return list(self.nodes.values())


class FakeTaskRepository(ITaskRepository):
    """In-memory task repository for unit tests."""

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    async def save(self, task: Task) -> None:
        self.tasks[task.id] = task

    async def find_by_id(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    async def find_by_id_for_update(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    async def find_by_idempotency_key(self, key: str) -> Task | None:
        for task in self.tasks.values():
            if task.idempotency_key == key:
                return task
        return None


class FakeTelemetryRepository(ITelemetryRepository):
    """In-memory telemetry repository for unit tests."""

    def __init__(self) -> None:
        self.metrics: list[TelemetryMetric] = []

    async def save_metric(self, metric: TelemetryMetric) -> None:
        self.metrics.append(metric)

    async def get_latest_metrics_for_node(self, node_id: str, limit: int = 10) -> list[TelemetryMetric]:
        node_metrics = [m for m in self.metrics if m.node_id == node_id]
        # Sort descending by timestamp
        node_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        return node_metrics[:limit]


class FakeEventPublisher(IEventPublisher):
    """Event publisher double that records published events for assertions."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish_node_registered(self, node: Node) -> None:
        self.events.append({"type": "node_registered", "data": node})

    async def publish_task_dispatched(self, task: Task) -> None:
        self.events.append({"type": "task_dispatched", "data": task})

    async def publish_task_status_changed(self, task: Task) -> None:
        self.events.append({"type": "task_status_changed", "data": task})

    async def publish_telemetry_ingested(self, metric: TelemetryMetric) -> None:
        self.events.append({"type": "telemetry_ingested", "data": metric})

