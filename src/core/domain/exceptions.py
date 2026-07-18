class DomainException(Exception):
    """Base exception class for all domain-related errors."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NodeNotFoundError(DomainException):
    """Raised when a requested node does not exist in the system."""
    def __init__(self, node_id: str) -> None:
        super().__init__(f"Worker node with ID '{node_id}' was not found.")
        self.node_id = node_id


class DuplicateNodeError(DomainException):
    """Raised when attempting to register a node that already exists."""
    def __init__(self, hostname: str) -> None:
        super().__init__(f"A node with hostname '{hostname}' is already registered.")
        self.hostname = hostname


class TaskNotFoundError(DomainException):
    """Raised when a requested task does not exist in the system."""
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task with ID '{task_id}' was not found.")
        self.task_id = task_id


class NodeOfflineException(DomainException):
    """Raised when trying to assign work to a node that is offline."""
    def __init__(self, node_id: str) -> None:
        super().__init__(f"Worker node '{node_id}' is offline and cannot accept tasks.")
        self.node_id = node_id


class InvalidTaskStateException(DomainException):
    """Raised when a task transitions into an invalid state."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
