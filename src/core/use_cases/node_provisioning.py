import uuid
from datetime import UTC, datetime
from typing import Any

from src.core.domain.entities import Node, NodeStatus
from src.core.domain.exceptions import DuplicateNodeError, NodeNotFoundError
from src.core.ports.interfaces import IEventPublisher, INodeProvisioningUseCase, INodeRepository


class NodeProvisioningService(INodeProvisioningUseCase):
    def __init__(self, node_repository: INodeRepository, event_publisher: IEventPublisher) -> None:
        self._node_repository: INodeRepository = node_repository
        self._event_publisher: IEventPublisher = event_publisher

    async def register_node(self, hostname: str, hardware_specs: dict[str, Any]) -> Node:
        existing_node = await self._node_repository.find_by_hostname(hostname)
        if existing_node is not None:
            raise DuplicateNodeError(hostname)

        new_node = Node(
            id=str(uuid.uuid4()),
            hostname=hostname,
            status=NodeStatus.ONLINE,
            hardware_specs=hardware_specs,
            last_heartbeat=datetime.now(UTC)
        )
        await self._node_repository.save(new_node)
        await self._event_publisher.publish_node_registered(new_node)
        return new_node

    async def process_heartbeat(self, node_id: str) -> None:
        node = await self._node_repository.find_by_id(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)

        updated_node = node.update_heartbeat(datetime.now(UTC))
        await self._node_repository.save(updated_node)

    async def list_nodes(self) -> list[Node]:
        return await self._node_repository.list_all()

