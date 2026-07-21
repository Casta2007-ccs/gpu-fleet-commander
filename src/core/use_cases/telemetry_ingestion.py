from datetime import UTC, datetime

from src.core.domain.entities import TelemetryMetric
from src.core.domain.exceptions import NodeNotFoundError
from src.core.ports.interfaces import IEventPublisher, INodeRepository, ITelemetryIngestionUseCase, ITelemetryRepository


class TelemetryIngestionService(ITelemetryIngestionUseCase):
    """Business service implementation for telemetry ingestion."""

    def __init__(
        self,
        node_repository: INodeRepository,
        telemetry_repository: ITelemetryRepository,
        event_publisher: IEventPublisher | None = None
    ) -> None:
        self._node_repository: INodeRepository = node_repository
        self._telemetry_repository: ITelemetryRepository = telemetry_repository
        self._event_publisher: IEventPublisher | None = event_publisher

    async def ingest_metrics(self, node_id: str, cpu_usage: float, gpu_usage: float, temperature: float) -> TelemetryMetric:
        node = await self._node_repository.find_by_id(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)

        metric = TelemetryMetric(
            node_id=node_id,
            timestamp=datetime.now(UTC),
            cpu_usage=cpu_usage,
            gpu_usage=gpu_usage,
            temperature=temperature
        )
        await self._telemetry_repository.save_metric(metric)
        if self._event_publisher is not None:
            await self._event_publisher.publish_telemetry_ingested(metric)
        return metric

    async def get_latest_telemetry(self, node_id: str, limit: int = 10) -> list[TelemetryMetric]:
        node = await self._node_repository.find_by_id(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)
        return await self._telemetry_repository.get_latest_metrics_for_node(node_id, limit)


