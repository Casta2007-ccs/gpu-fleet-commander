from datetime import datetime, timezone
from src.core.domain.entities import TelemetryMetric
from src.core.domain.exceptions import NodeNotFoundError
from src.core.ports.interfaces import ITelemetryIngestionUseCase, INodeRepository, ITelemetryRepository


class TelemetryIngestionService(ITelemetryIngestionUseCase):
    """Business service implementation for telemetry ingestion."""

    def __init__(self, node_repository: INodeRepository, telemetry_repository: ITelemetryRepository) -> None:
        self._node_repository: INodeRepository = node_repository
        self._telemetry_repository: ITelemetryRepository = telemetry_repository

    async def ingest_metrics(self, node_id: str, cpu_usage: float, gpu_usage: float, temperature: float) -> TelemetryMetric:
        node = await self._node_repository.find_by_id(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)

        metric = TelemetryMetric(
            node_id=node_id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=cpu_usage,
            gpu_usage=gpu_usage,
            temperature=temperature
        )
        await self._telemetry_repository.save_metric(metric)
        return metric
