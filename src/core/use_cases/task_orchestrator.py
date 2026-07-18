import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from src.core.domain.entities import Task, TaskStatus, NodeStatus
from src.core.domain.exceptions import TaskNotFoundError, NodeNotFoundError, NodeOfflineException
from src.core.ports.interfaces import ITaskOrchestratorUseCase, ITaskRepository, INodeRepository, IEventPublisher


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

    def create_task(self, idempotency_key: str, payload: Dict[str, Any]) -> Task:
        existing_task = self._task_repository.find_by_idempotency_key(idempotency_key)
        if existing_task is not None:
            return existing_task

        new_task = Task(
            id=str(uuid.uuid4()),
            payload=payload,
            status=TaskStatus.PENDING,
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc)
        )
        self._task_repository.save(new_task)
        return new_task

    def dispatch_task(self, task_id: str, node_id: str) -> Task:
        task = self._task_repository.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        node = self._node_repository.find_by_id(node_id)
        if node is None:
            raise NodeNotFoundError(node_id)

        if node.status != NodeStatus.ONLINE:
            raise NodeOfflineException(node_id)

        updated_task = task.assign_to_node(node.id)
        self._task_repository.save(updated_task)
        self._event_publisher.publish_task_dispatched(updated_task)
        return updated_task

    def transition_task(self, task_id: str, status: TaskStatus) -> Task:
        task = self._task_repository.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        now = datetime.now(timezone.utc)
        if status == TaskStatus.COMPLETED:
            updated_task = task.complete(now)
        elif status == TaskStatus.FAILED:
            updated_task = task.fail(now)
        else:
            raise ValueError(f"Invalid transition target status for core update: {status}")

        self._task_repository.save(updated_task)
        self._event_publisher.publish_task_status_changed(updated_task)
        return updated_task
