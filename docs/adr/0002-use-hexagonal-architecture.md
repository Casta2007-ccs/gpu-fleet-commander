# 2. Use Hexagonal Architecture (Ports and Adapters)

Date: 2026-07-18

## Status
Accepted

## Context
When building distributed control planes, framework lock-in (e.g. coupling business logic to FastAPI, SQLAlchemy, or specific SQL drivers) makes it difficult to upgrade components, swap technologies, or write fast unit tests without complex database mocking setups. We need a design that isolates business logic and makes it fully framework-agnostic.

## Decision
We will enforce **Hexagonal Architecture** (also known as Ports and Adapters) across the repository:
1. **Core Domain**: Contains pure domain entities, business validation, and custom exceptions. Imports no external libraries.
2. **Ports**: Interfaces (Abstract Base Classes) defining inbound capabilities (Use Cases) and outbound capabilities (SPIs).
3. **Adapters**: Concrete implementations (FastAPI routers, Pydantic schemas, SQLAlchemy repositories, event brokers) that interact with external networks, databases, and message brokers.

All source dependencies must point inward: `Adapters -> Ports -> Core Domain`.

## Consequences
- **High Testability**: The core business rules can be verified using mock doubles (Fakes) without a database or API running, resulting in unit tests that execute in milliseconds.
- **Portability**: We can change the delivery mechanisms (e.g., from REST to gRPC) or storage mechanisms (e.g., from Postgres to InfluxDB or Redis) by writing new adapters without touching the core code.
- **Decoupling overhead**: Requires writing boilerplate mappings from ORM schemas to Domain Entities and DTO Pydantic models.
