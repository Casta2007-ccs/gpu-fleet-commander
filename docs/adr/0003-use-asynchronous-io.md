# 3. Use Asynchronous I/O (Async/Await)

Date: 2026-07-18

## Status
Accepted

## Context
Orchestrating distributed worker nodes involves high-frequency telemetry ingestion (sub-second keepalive signals, cpu/gpu/temp metrics) and concurrent task dispatching. Using a synchronous execution model in Python (which blocks threads on database calls) would lead to resource starvation under load, causing latency spikes in heartbeat processing.

## Decision
We will design the control plane using **Asynchronous I/O** at all network and database layers:
1. **Framework**: FastAPI configured to use asynchronous route handlers (`async def`).
2. **Database Engine**: SQLAlchemy 2.0 configured with `AsyncSession` and the asynchronous `asyncpg` PostgreSQL driver.
3. **Core Contracts**: All port methods defined as `async def` and awaited appropriately in use case implementations.

## Consequences
- **Performance**: High concurrency with low CPU overhead due to non-blocking I/O multiplexing.
- **Complexity**: Requires careful handling of asynchronous event loops, preventing synchronous blocks (like `time.sleep()`), and using async-compatible test extensions (`pytest-asyncio`).
- **Driver limits**: Third-party libraries must support asynchronous clients (e.g. `asyncpg` for Postgres, `redis-py` async client).
