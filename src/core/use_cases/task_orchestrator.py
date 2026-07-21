import uuid
from datetime import UTC, datetime
from typing import Any

from src.core.domain.entities import NodeStatus, Task, TaskStatus
from src.core.domain.exceptions import (
    InvalidTransitionTargetError,
    NodeNotFoundError,
    NodeOfflineException,
    TaskNotFoundError,
)
from src.core.ports.interfaces import IEventPublisher, INodeRepository, ITaskOrchestratorUseCase, ITaskRepository


class TaskOrchestratorService(ITaskOrchestratorUseCase):
    def __init__(
        self,
        task_repository: ITaskRepository,
        node_repository: INodeRepository,
        event_publisher: IEventPublisher
    ) -> None:
        self._task_repository: ITaskRepository = task_repository
        self._node_repository: INodeRepository = node_repository
        self._event_publisher: IEventPublisher = event_publisher

    async def create_task(self, idempotency_key: str, payload: dict[str, Any]) -> Task:
        existing_task = await self._task_repository.find_by_idempotency_key(idempotency_key)
        if existing_task is not None:
            return existing_task

        new_task = Task(
            id=str(uuid.uuid4()),
            payload=payload,
            status=TaskStatus.PENDING,
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC)
        )
        await self._task_repository.save(new_task)
        return new_task

    async def dispatch_task(self, task_id: str, node_id: str) -> Task:
        task = await self._task_repository.find_by_id_for_update(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        node = await self._node_repository.find_by_id_for_update(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)

        if node.status != NodeStatus.ONLINE:
            raise NodeOfflineException(node_id)

        updated_task = task.assign_to_node(node.id)
        await self._task_repository.save(updated_task)
        await self._event_publisher.publish_task_dispatched(updated_task)
        return updated_task

    async def transition_task(self, task_id: str, status: TaskStatus) -> Task:
        task = await self._task_repository.find_by_id_for_update(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        now = datetime.now(UTC)
        if status == TaskStatus.COMPLETED:
            updated_task = task.complete(now)
        elif status == TaskStatus.FAILED:
            updated_task = task.fail(now)
        else:
            raise InvalidTransitionTargetError(str(status.value))

        await self._task_repository.save(updated_task)
        await self._event_publisher.publish_task_status_changed(updated_task)
        return updated_task

    async def get_task(self, task_id: str) -> Task:
        task = await self._task_repository.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

