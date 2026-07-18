import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from src.core.domain.entities import Node, NodeStatus
from src.core.domain.exceptions import DuplicateNodeError, NodeNotFoundError
from src.core.ports.interfaces import INodeProvisioningUseCase, INodeRepository, IEventPublisher


class NodeProvisioningService(INodeProvisioningUseCase):
    def __init__(self, node_repository: INodeRepository, event_publisher: IEventPublisher) -> None:
        self._node_repository: INodeRepository = node_repository
        self._event_publisher: IEventPublisher = event_publisher

    def register_node(self, hostname: str, hardware_specs: Dict[str, Any]) -> Node:
        existing_node = self._node_repository.find_by_hostname(hostname)
        if existing_node is not None:
            raise DuplicateNodeError(hostname)

        new_node = Node(
            id=str(uuid.uuid4()),
            hostname=hostname,
            status=NodeStatus.ONLINE,
            hardware_specs=hardware_specs,
            last_heartbeat=datetime.now(timezone.utc)
        )
        self._node_repository.save(new_node)
        self._event_publisher.publish_node_registered(new_node)
        return new_node

    def process_heartbeat(self, node_id: str) -> None:
        node = self._node_repository.find_by_id(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)

        updated_node = node.update_heartbeat(datetime.now(timezone.utc))
        self._node_repository.save(updated_node)
