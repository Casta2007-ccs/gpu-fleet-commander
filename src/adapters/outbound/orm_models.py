from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.adapters.outbound.database import Base
from src.core.domain.entities import NodeStatus, TaskStatus


class NodeORM(Base):
    """Database representation of a worker node."""
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus, native_enum=False), nullable=False)
    hardware_specs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskORM(Base):
    """Database representation of a computational task."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, native_enum=False), nullable=False)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("nodes.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)


class TelemetryMetricORM(Base):
    """Database representation of high-frequency hardware telemetry."""
    __tablename__ = "telemetry_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(36), ForeignKey("nodes.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cpu_usage: Mapped[float] = mapped_column(Float, nullable=False)
    gpu_usage: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)

