from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.core.domain.entities import NodeStatus, TaskStatus

# --- Nodes Schemas ---

class NodeRegisterRequest(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255, description="Unique hostname of the node")
    hardware_specs: dict[str, Any] = Field(..., description="JSON representing hardware details (GPU info, memory, etc.)")


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hostname: str
    status: NodeStatus
    hardware_specs: dict[str, Any]
    last_heartbeat: datetime


# --- Tasks Schemas ---

class TaskCreateRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=255, description="Client-provided idempotency token")
    payload: dict[str, Any] = Field(..., description="Parameters required for executing the task")


class DispatchRequest(BaseModel):
    """Request body for dispatching a task to a specific node."""
    node_id: str = Field(..., min_length=1, max_length=36, description="Target node ID to dispatch the task to")


class TransitionRequest(BaseModel):
    """Request body for transitioning a task to a new status."""
    target_status: TaskStatus = Field(..., description="Target status (COMPLETED or FAILED)")


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payload: dict[str, Any]
    status: TaskStatus
    retries: int
    node_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


# --- Telemetry Schemas ---

class TelemetryIngestRequest(BaseModel):
    cpu_usage: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    gpu_usage: float = Field(..., ge=0.0, le=100.0, description="GPU usage percentage")
    temperature: float = Field(..., ge=-273.15, description="Temperature in Celsius")


class TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    timestamp: datetime
    cpu_usage: float
    gpu_usage: float
    temperature: float
