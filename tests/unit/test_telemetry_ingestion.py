from datetime import UTC, datetime

import pytest

from src.core.domain.entities import Node, NodeStatus
from src.core.domain.exceptions import NodeNotFoundError
from src.core.use_cases.telemetry_ingestion import TelemetryIngestionService
from tests.unit.fakes import FakeNodeRepository, FakeTelemetryRepository


@pytest.fixture
def node_repo() -> FakeNodeRepository:
    return FakeNodeRepository()


@pytest.fixture
def telemetry_repo() -> FakeTelemetryRepository:
    return FakeTelemetryRepository()


@pytest.fixture
def service(node_repo: FakeNodeRepository, telemetry_repo: FakeTelemetryRepository) -> TelemetryIngestionService:
    return TelemetryIngestionService(node_repo, telemetry_repo)


@pytest.mark.asyncio
async def test_ingest_metrics_success(
    service: TelemetryIngestionService,
    node_repo: FakeNodeRepository,
    telemetry_repo: FakeTelemetryRepository
):
    node = Node("node-100", "nv-host-100", NodeStatus.ONLINE, {}, datetime.now(UTC))
    await node_repo.save(node)

    metric = await service.ingest_metrics("node-100", cpu_usage=25.5, gpu_usage=88.0, temperature=62.5)

    assert metric.node_id == "node-100"
    assert metric.cpu_usage == 25.5
    assert metric.gpu_usage == 88.0
    assert metric.temperature == 62.5

    saved = await telemetry_repo.get_latest_metrics_for_node("node-100")
    assert len(saved) == 1
    assert saved[0].cpu_usage == 25.5


@pytest.mark.asyncio
async def test_ingest_metrics_node_not_found_raises_error(service: TelemetryIngestionService):
    with pytest.raises(NodeNotFoundError):
        await service.ingest_metrics("non-existent-node", 50.0, 50.0, 50.0)


@pytest.mark.asyncio
async def test_get_latest_telemetry_success(
    service: TelemetryIngestionService,
    node_repo: FakeNodeRepository
):
    node = Node("node-100", "nv-host-100", NodeStatus.ONLINE, {}, datetime.now(UTC))
    await node_repo.save(node)

    await service.ingest_metrics("node-100", cpu_usage=10.0, gpu_usage=20.0, temperature=40.0)
    await service.ingest_metrics("node-100", cpu_usage=30.0, gpu_usage=60.0, temperature=55.0)

    metrics = await service.get_latest_telemetry("node-100", limit=5)
    assert len(metrics) == 2


@pytest.mark.asyncio
async def test_get_latest_telemetry_node_not_found_raises_error(service: TelemetryIngestionService):
    with pytest.raises(NodeNotFoundError):
        await service.get_latest_telemetry("non-existent-node", limit=5)
