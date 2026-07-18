from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from src.core.domain.exceptions import InvalidTaskStateException


class NodeStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Node:
    id: str
    hostname: str
    status: NodeStatus
    hardware_specs: Dict[str, Any]
    last_heartbeat: datetime

    def __post_init__(self) -> None:
        # Strict validation
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Node ID must be a non-empty string.")
        if not isinstance(self.hostname, str) or not self.hostname.strip():
            raise ValueError("Hostname must be a non-empty string.")
        if not isinstance(self.status, NodeStatus):
            raise TypeError("status must be an instance of NodeStatus.")
        if not isinstance(self.hardware_specs, dict):
            raise TypeError("hardware_specs must be a dictionary.")
        if not isinstance(self.last_heartbeat, datetime):
            raise TypeError("last_heartbeat must be a datetime instance.")

    def update_heartbeat(self, timestamp: datetime) -> "Node":
        if not isinstance(timestamp, datetime):
            raise TypeError("Heartbeat timestamp must be a datetime instance.")
        return replace(self, last_heartbeat=timestamp, status=NodeStatus.ONLINE)

    def mark_offline(self) -> "Node":
        return replace(self, status=NodeStatus.OFFLINE)


@dataclass(frozen=True)
class Task:
    id: str
    payload: Dict[str, Any]
    status: TaskStatus
    idempotency_key: str
    retries: int = 0
    node_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Task ID must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise TypeError("Payload must be a dictionary.")
        if not isinstance(self.status, TaskStatus):
            raise TypeError("status must be an instance of TaskStatus.")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise ValueError("Idempotency key must be a non-empty string.")
        if not isinstance(self.retries, int) or self.retries < 0:
            raise ValueError("Retries must be a non-negative integer.")

    def assign_to_node(self, node_id: str) -> "Task":
        if self.status != TaskStatus.PENDING:
            raise InvalidTaskStateException(
                f"Cannot assign task '{self.id}' in state '{self.status.value}' to node."
            )
        return replace(self, node_id=node_id, status=TaskStatus.RUNNING)

    def complete(self, timestamp: datetime) -> "Task":
        if self.status != TaskStatus.RUNNING:
            raise InvalidTaskStateException(
                f"Cannot complete task '{self.id}' because it is in state '{self.status.value}'."
            )
        return replace(self, status=TaskStatus.COMPLETED, completed_at=timestamp)

    def fail(self, timestamp: datetime) -> "Task":
        if self.status != TaskStatus.RUNNING:
            raise InvalidTaskStateException(
                f"Cannot fail task '{self.id}' because it is in state '{self.status.value}'."
            )
        return replace(self, status=TaskStatus.FAILED, completed_at=timestamp, retries=self.retries + 1)


@dataclass(frozen=True)
class TelemetryMetric:
    node_id: str
    timestamp: datetime
    cpu_usage: float
    gpu_usage: float
    temperature: float

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id.strip():
            raise ValueError("Node ID must be a non-empty string.")
        if not isinstance(self.timestamp, datetime):
            raise TypeError("Timestamp must be a datetime instance.")
        if not (0.0 <= self.cpu_usage <= 100.0):
            raise ValueError("CPU usage must be between 0.0 and 100.0 percent.")
        if not (0.0 <= self.gpu_usage <= 100.0):
            raise ValueError("GPU usage must be between 0.0 and 100.0 percent.")
        if self.temperature < -273.15:  # Absolute zero
            raise ValueError("Temperature cannot be below absolute zero.")
