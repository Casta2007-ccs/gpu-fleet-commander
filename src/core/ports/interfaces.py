from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.core.domain.entities import Node, Task, TaskStatus, TelemetryMetric


# ==============================================================================
# INBOUND PORTS (Driving Ports / Use Cases)
# ==============================================================================

class INodeProvisioningUseCase(ABC):
    """Port defining operations for provisioning and monitoring worker nodes.

    Adapters (such as REST APIs or gRPC services) call this port to register
    nodes or record heartbeat signals.
    """

    @abstractmethod
    def register_node(self, hostname: str, hardware_specs: Dict[str, Any]) -> Node:
        """Register a new worker node in the system.

        Args:
            hostname: The unique network name of the node.
            hardware_specs: Specifications of the node, such as GPU models, memory, etc.

        Returns:
            The registered Node domain entity.

        Raises:
            DuplicateNodeError: If a node with the same hostname already exists.
        """

    @abstractmethod
    def process_heartbeat(self, node_id: str) -> None:
        """Record a heartbeat signal from a worker node.

        Args:
            node_id: The unique identifier of the node.

        Raises:
            NodeNotFoundError: If the node does not exist.
        """


class ITaskOrchestratorUseCase(ABC):
    """Port defining operations for managing and dispatching tasks to worker nodes.

    Adapters call this port to schedule computational tasks or update task execution states.
    """

    @abstractmethod
    def create_task(self, idempotency_key: str, payload: Dict[str, Any]) -> Task:
        """Create a new task ensuring idempotency.

        Args:
            idempotency_key: Unique client-provided token to prevent duplicate task creation.
            payload: Parameters and configuration required to execute the task.

        Returns:
            The created or already existing Task entity.
        """

    @abstractmethod
    def dispatch_task(self, task_id: str, node_id: str) -> Task:
        """Assign and dispatch a pending task to an online node.

        Args:
            task_id: The unique identifier of the task to dispatch.
            node_id: The identifier of the worker node designated for execution.

        Returns:
            The updated Task entity in RUNNING state.

        Raises:
            TaskNotFoundError: If the task does not exist.
            NodeNotFoundError: If the node does not exist.
            NodeOfflineException: If the node status is not ONLINE.
            InvalidTaskStateException: If the task is not in PENDING state.
        """

    @abstractmethod
    def transition_task(self, task_id: str, status: TaskStatus) -> Task:
        """Transition a running task to completed or failed state.

        Args:
            task_id: The unique identifier of the task.
            status: The target status (COMPLETED or FAILED).

        Returns:
            The updated Task entity.

        Raises:
            TaskNotFoundError: If the task does not exist.
            InvalidTaskStateException: If the transition is not allowed.
        """


class ITelemetryIngestionUseCase(ABC):
    """Port defining operations for ingesting periodic metrics from worker nodes.

    Adapters call this port to process stream telemetry data (CPU, GPU, Temp).
    """

    @abstractmethod
    def ingest_metrics(self, node_id: str, cpu_usage: float, gpu_usage: float, temperature: float) -> TelemetryMetric:
        """Ingest metrics collected from a worker node.

        Args:
            node_id: The identifier of the reporting node.
            cpu_usage: Percentage CPU usage (0.0 to 100.0).
            gpu_usage: Percentage GPU usage (0.0 to 100.0).
            temperature: Current node temperature in Celsius.

        Returns:
            The created TelemetryMetric domain entity.

        Raises:
            NodeNotFoundError: If the reporting node is not registered.
        """


# ==============================================================================
# OUTBOUND PORTS (Driven Ports / SPIs)
# ==============================================================================

class INodeRepository(ABC):
    """Port for persisting and retrieving worker node domain states.

    Database adapters must implement this interface to support persistence engines (SQL/NoSQL).
    """

    @abstractmethod
    def save(self, node: Node) -> None:
        """Persist a node's domain state.

        Args:
            node: The Node entity to save.
        """

    @abstractmethod
    def find_by_id(self, node_id: str) -> Optional[Node]:
        """Retrieve a node by its unique identifier.

        Args:
            node_id: The identifier to look up.

        Returns:
            The Node entity if found, otherwise None.
        """

    @abstractmethod
    def find_by_hostname(self, hostname: str) -> Optional[Node]:
        """Retrieve a node by its hostname.

        Args:
            hostname: The hostname to search for.

        Returns:
            The Node entity if found, otherwise None.
        """

    @abstractmethod
    def list_all(self) -> List[Node]:
        """Retrieve all nodes in the system.

        Returns:
            A list containing all registered Node entities.
        """


class ITaskRepository(ABC):
    """Port for persisting and retrieving task domain states.

    Database adapters must implement this interface.
    """

    @abstractmethod
    def save(self, task: Task) -> None:
        """Persist a task's domain state.

        Args:
            task: The Task entity to save.
        """

    @abstractmethod
    def find_by_id(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by its unique identifier.

        Args:
            task_id: The identifier to look up.

        Returns:
            The Task entity if found, otherwise None.
        """

    @abstractmethod
    def find_by_idempotency_key(self, key: str) -> Optional[Task]:
        """Retrieve a task by its idempotency key.

        Args:
            key: The idempotency key to look up.

        Returns:
            The Task entity if found, otherwise None.
        """


class ITelemetryRepository(ABC):
    """Port for persisting node time-series metrics.

    Time-series database or traditional database adapters must implement this.
    """

    @abstractmethod
    def save_metric(self, metric: TelemetryMetric) -> None:
        """Persist a telemetry metric data point.

        Args:
            metric: The TelemetryMetric entity to save.
        """

    @abstractmethod
    def get_latest_metrics_for_node(self, node_id: str, limit: int = 10) -> List[TelemetryMetric]:
        """Retrieve the most recent metrics for a given node.

        Args:
            node_id: The identifier of the node.
            limit: Maximum number of data points to return.

        Returns:
            A list of TelemetryMetric entities.
        """


class IEventPublisher(ABC):
    """Port for dispatching domain events to external messaging brokers (Kafka/Redis/RabbitMQ)."""

    @abstractmethod
    def publish_node_registered(self, node: Node) -> None:
        """Publish an event notifying that a node has been registered.

        Args:
            node: The Node that registered.
        """

    @abstractmethod
    def publish_task_dispatched(self, task: Task) -> None:
        """Publish an event notifying that a task has been dispatched.

        Args:
            task: The Task that was dispatched.
        """

    @abstractmethod
    def publish_task_status_changed(self, task: Task) -> None:
        """Publish an event notifying that a task status has transitioned.

        Args:
            task: The updated Task entity.
        """
