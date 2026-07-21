import logging

from src.adapters.inbound.websocket_manager import manager
from src.core.domain.entities import Node, Task, TelemetryMetric
from src.core.ports.interfaces import IEventPublisher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EventPublisher")


class LoggingEventPublisher(IEventPublisher):
    """An event publisher adapter that logs events to stdout and forwards telemetry to WebSocket manager."""

    async def publish_node_registered(self, node: Node) -> None:
        logger.info(f"Event: NodeRegistered - ID: {node.id}, Hostname: {node.hostname}")

    async def publish_task_dispatched(self, task: Task) -> None:
        logger.info(f"Event: TaskDispatched - ID: {task.id}, AssignedNodeID: {task.node_id}")

    async def publish_task_status_changed(self, task: Task) -> None:
        logger.info(f"Event: TaskStatusChanged - ID: {task.id}, NewStatus: {task.status.value}")

    async def publish_telemetry_ingested(self, metric: TelemetryMetric) -> None:
        logger.info(f"Event: TelemetryIngested - NodeID: {metric.node_id}, CPU: {metric.cpu_usage}%, GPU: {metric.gpu_usage}%")
        await manager.publish_telemetry({
            "node_id": metric.node_id,
            "timestamp": metric.timestamp.isoformat(),
            "cpu_usage": metric.cpu_usage,
            "gpu_usage": metric.gpu_usage,
            "temperature": metric.temperature
        })

