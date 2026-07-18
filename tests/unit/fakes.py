from typing import Any, Dict, List, Optional
from src.core.domain.entities import Node, Task, TelemetryMetric
from src.core.ports.interfaces import INodeRepository, ITaskRepository, ITelemetryRepository, IEventPublisher


class FakeNodeRepository(INodeRepository):
    """In-memory node repository for unit tests."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}

    async def save(self, node: Node) -> None:
        self.nodes[node.id] = node

    async def find_by_id(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    async def find_by_hostname(self, hostname: str) -> Optional[Node]:
        for node in self.nodes.values():
            if node.hostname == hostname:
                return node
        return None

    async def list_all(self) -> List[Node]:
        return list(self.nodes.values())


class FakeTaskRepository(ITaskRepository):
    """In-memory task repository for unit tests."""

    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}

    async def save(self, task: Task) -> None:
        self.tasks[task.id] = task

    async def find_by_id(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    async def find_by_idempotency_key(self, key: str) -> Optional[Task]:
        for task in self.tasks.values():
            if task.idempotency_key == key:
                return task
        return None


class FakeTelemetryRepository(ITelemetryRepository):
    """In-memory telemetry repository for unit tests."""

    def __init__(self) -> None:
        self.metrics: List[TelemetryMetric] = []

    async def save_metric(self, metric: TelemetryMetric) -> None:
        self.metrics.append(metric)

    async def get_latest_metrics_for_node(self, node_id: str, limit: int = 10) -> List[TelemetryMetric]:
        node_metrics = [m for m in self.metrics if m.node_id == node_id]
        # Sort descending by timestamp
        node_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        return node_metrics[:limit]


class FakeEventPublisher(IEventPublisher):
    """Event publisher double that records published events for assertions."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    async def publish_node_registered(self, node: Node) -> None:
        self.events.append({"type": "node_registered", "data": node})

    async def publish_task_dispatched(self, task: Task) -> None:
        self.events.append({"type": "task_dispatched", "data": task})

    async def publish_task_status_changed(self, task: Task) -> None:
        self.events.append({"type": "task_status_changed", "data": task})
