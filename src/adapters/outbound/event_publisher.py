import logging

from src.core.domain.entities import Node, Task
from src.core.ports.interfaces import IEventPublisher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoggingEventPublisher")


class LoggingEventPublisher(IEventPublisher):
    """An event publisher adapter that logs events to stdout.

    Acts as a lightweight placeholder before integrating real message brokers like Kafka/Redis.
    """

    async def publish_node_registered(self, node: Node) -> None:
        logger.info(f"Event: NodeRegistered - ID: {node.id}, Hostname: {node.hostname}")

    async def publish_task_dispatched(self, task: Task) -> None:
        logger.info(f"Event: TaskDispatched - ID: {task.id}, AssignedNodeID: {task.node_id}")

    async def publish_task_status_changed(self, task: Task) -> None:
        logger.info(f"Event: TaskStatusChanged - ID: {task.id}, NewStatus: {task.status.value}")
