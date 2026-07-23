from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.outbound.orm_models import NodeORM, TaskORM, TelemetryMetricORM
from src.core.domain.entities import NodeStatus, TaskStatus


async def generate_prometheus_metrics(session: AsyncSession) -> str:
    """Queries current database states and formats Prometheus exposition metrics."""
    # Count nodes by status
    node_stmt = select(NodeORM.status, func.count(NodeORM.id)).group_by(NodeORM.status)
    node_results = await session.execute(node_stmt)
    node_counts = dict.fromkeys(NodeStatus, 0)
    for status_val, count in node_results.all():
        if status_val in node_counts:
            node_counts[status_val] = count

    # Count tasks by status
    task_stmt = select(TaskORM.status, func.count(TaskORM.id)).group_by(TaskORM.status)
    task_results = await session.execute(task_stmt)
    task_counts = dict.fromkeys(TaskStatus, 0)
    for status_val, count in task_results.all():
        if status_val in task_counts:
            task_counts[status_val] = count

    # Total telemetry metrics count
    telemetry_stmt = select(func.count(TelemetryMetricORM.id))
    telemetry_result = await session.execute(telemetry_stmt)
    telemetry_total = telemetry_result.scalar_one() or 0

    lines: list[str] = [
        "# HELP gpu_fleet_nodes_total Total registered worker nodes grouped by status.",
        "# TYPE gpu_fleet_nodes_total gauge",
    ]
    for node_status, count in node_counts.items():
        lines.append(f'gpu_fleet_nodes_total{{status="{node_status.value}"}} {count}')

    lines.extend([
        "",
        "# HELP gpu_fleet_tasks_total Total computational tasks grouped by status.",
        "# TYPE gpu_fleet_tasks_total gauge",
    ])
    for task_status, count in task_counts.items():
        lines.append(f'gpu_fleet_tasks_total{{status="{task_status.value}"}} {count}')


    lines.extend([
        "",
        "# HELP gpu_fleet_telemetry_metrics_total Total ingested hardware telemetry data points.",
        "# TYPE gpu_fleet_telemetry_metrics_total counter",
        f"gpu_fleet_telemetry_metrics_total {telemetry_total}",
        ""
    ])

    return "\n".join(lines)
