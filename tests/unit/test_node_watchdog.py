from datetime import UTC, datetime, timedelta

import pytest

from src.core.domain.entities import Node, NodeStatus
from src.core.use_cases.node_provisioning import NodeProvisioningService
from src.core.use_cases.telemetry_ingestion import TelemetryIngestionService
from tests.unit.fakes import FakeEventPublisher, FakeNodeRepository, FakeTelemetryRepository


@pytest.mark.asyncio
async def test_check_stale_nodes_marks_inactive_nodes_offline() -> None:
    repo = FakeNodeRepository()
    publisher = FakeEventPublisher()
    service = NodeProvisioningService(repo, publisher)

    now = datetime.now(UTC)
    active_node = Node(
        id="node-active",
        hostname="active-gpu",
        status=NodeStatus.ONLINE,
        hardware_specs={"gpu": "RTX 4090"},
        last_heartbeat=now - timedelta(seconds=10)
    )
    stale_node = Node(
        id="node-stale",
        hostname="stale-gpu",
        status=NodeStatus.ONLINE,
        hardware_specs={"gpu": "H100"},
        last_heartbeat=now - timedelta(seconds=45)
    )

    await repo.save(active_node)
    await repo.save(stale_node)

    offline_count = await service.check_stale_nodes(timeout_seconds=30)

    assert offline_count == 1
    updated_active = await repo.find_by_id("node-active")
    updated_stale = await repo.find_by_id("node-stale")

    assert updated_active is not None and updated_active.status == NodeStatus.ONLINE
    assert updated_stale is not None and updated_stale.status == NodeStatus.OFFLINE


@pytest.mark.asyncio
async def test_telemetry_ingestion_publishes_event() -> None:
    node_repo = FakeNodeRepository()
    telemetry_repo = FakeTelemetryRepository()
    publisher = FakeEventPublisher()

    node = Node(
        id="node-1",
        hostname="test-gpu",
        status=NodeStatus.ONLINE,
        hardware_specs={},
        last_heartbeat=datetime.now(UTC)
    )
    await node_repo.save(node)

    service = TelemetryIngestionService(node_repo, telemetry_repo, publisher)
    await service.ingest_metrics("node-1", cpu_usage=50.0, gpu_usage=80.0, temperature=65.0)

    assert len(publisher.events) == 1
    assert publisher.events[0]["type"] == "telemetry_ingested"
    assert publisher.events[0]["data"].node_id == "node-1"
