from datetime import datetime

import pytest

from src.core.domain.entities import NodeStatus
from src.core.domain.exceptions import DuplicateNodeError, NodeNotFoundError
from src.core.use_cases.node_provisioning import NodeProvisioningService
from tests.unit.fakes import FakeEventPublisher, FakeNodeRepository


@pytest.fixture
def node_repo() -> FakeNodeRepository:
    return FakeNodeRepository()


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def service(node_repo: FakeNodeRepository, event_publisher: FakeEventPublisher) -> NodeProvisioningService:
    return NodeProvisioningService(node_repo, event_publisher)


@pytest.mark.asyncio
async def test_register_node_success(
    service: NodeProvisioningService,
    node_repo: FakeNodeRepository,
    event_publisher: FakeEventPublisher
):
    hostname = "nv-jetson-01"
    specs = {"gpu": "Orin Nano", "memory_gb": 8}

    node = await service.register_node(hostname, specs)

    # Assertions on returned Node
    assert node.id is not None
    assert node.hostname == hostname
    assert node.status == NodeStatus.ONLINE
    assert node.hardware_specs == specs
    assert isinstance(node.last_heartbeat, datetime)

    # Assertions on Repository persistence
    db_node = await node_repo.find_by_id(node.id)
    assert db_node is not None
    assert db_node.hostname == hostname

    # Assertions on published events
    assert len(event_publisher.events) == 1
    assert event_publisher.events[0]["type"] == "node_registered"
    assert event_publisher.events[0]["data"].id == node.id


@pytest.mark.asyncio
async def test_register_node_duplicate_hostname_raises_error(service: NodeProvisioningService):
    hostname = "nv-jetson-01"
    specs = {"gpu": "Orin Nano"}

    # Register first time
    await service.register_node(hostname, specs)

    # Attempt to register second time with same hostname
    with pytest.raises(DuplicateNodeError) as exc_info:
        await service.register_node(hostname, specs)

    assert hostname in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_heartbeat_success(service: NodeProvisioningService, node_repo: FakeNodeRepository):
    hostname = "nv-jetson-01"
    specs = {"gpu": "Orin Nano"}

    node = await service.register_node(hostname, specs)
    initial_heartbeat = node.last_heartbeat

    # Process heartbeat
    await service.process_heartbeat(node.id)

    # Check node in repository updated
    updated_node = await node_repo.find_by_id(node.id)
    assert updated_node is not None
    assert updated_node.last_heartbeat > initial_heartbeat
    assert updated_node.status == NodeStatus.ONLINE


@pytest.mark.asyncio
async def test_process_heartbeat_non_existent_node_raises_error(service: NodeProvisioningService):
    with pytest.raises(NodeNotFoundError):
        await service.process_heartbeat("non-existent-id")


@pytest.mark.asyncio
async def test_list_nodes_success(service: NodeProvisioningService):
    await service.register_node("node-1", {"gpu": "RTX 4090"})
    await service.register_node("node-2", {"gpu": "H100"})

    nodes = await service.list_nodes()
    assert len(nodes) == 2

