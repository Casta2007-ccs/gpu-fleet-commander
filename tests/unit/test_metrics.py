import pytest

from src.adapters.inbound.metrics_exporter import generate_prometheus_metrics
from src.adapters.outbound.database import AsyncSessionMaker, Base, engine


@pytest.mark.asyncio
async def test_generate_prometheus_metrics_format() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionMaker() as session:
        metrics_output = await generate_prometheus_metrics(session)

    assert "gpu_fleet_nodes_total" in metrics_output
    assert "gpu_fleet_tasks_total" in metrics_output
    assert "gpu_fleet_telemetry_metrics_total" in metrics_output
    assert 'status="ONLINE"' in metrics_output
    assert 'status="PENDING"' in metrics_output
