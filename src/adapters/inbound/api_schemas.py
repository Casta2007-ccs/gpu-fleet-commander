from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from src.core.domain.entities import NodeStatus, TaskStatus


# --- Nodes Schemas ---

class NodeRegisterRequest(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255, description="Unique hostname of the node")
    hardware_specs: Dict[str, Any] = Field(..., description="JSON representing hardware details (GPU info, memory, etc.)")


class NodeResponse(BaseModel):
    id: str
    hostname: str
    status: NodeStatus
    hardware_specs: Dict[str, Any]
    last_heartbeat: datetime

    class Config:
        from_attributes = True


# --- Tasks Schemas ---

class TaskCreateRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=255, description="Client-provided idempotency token")
    payload: Dict[str, Any] = Field(..., description="Parameters required for executing the task")


class TaskResponse(BaseModel):
    id: str
    payload: Dict[str, Any]
    status: TaskStatus
    retries: int
    node_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Telemetry Schemas ---

class TelemetryIngestRequest(BaseModel):
    cpu_usage: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    gpu_usage: float = Field(..., ge=0.0, le=100.0, description="GPU usage percentage")
    temperature: float = Field(..., ge=-273.15, description="Temperature in Celsius")


class TelemetryResponse(BaseModel):
    node_id: str
    timestamp: datetime
    cpu_usage: float
    gpu_usage: float
    temperature: float

    class Config:
        from_attributes = True
