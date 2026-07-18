# ⚡ GPU Fleet Commander ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Reproducible Env: Flox](https://img.shields.io/badge/environment-Flox-orange.svg)](https://flox.dev/)
[![Architecture: Hexagonal](https://img.shields.io/badge/architecture-Hexagonal-green.svg)](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))
[![Tests: 13 passed](https://img.shields.io/badge/tests-13%20passed-brightgreen.svg)]()

**GPU Fleet Commander** is an enterprise-grade, high-performance Control Plane designed for orchestrating distributed computing resources (such as server clusters or NVIDIA Jetson edge systems). It handles real-time node registration, heartbeat telemetry monitoring, and idempotent task dispatching.

Built with a **pure domain model** following strict **Hexagonal Architecture** (Ports and Adapters) principles, the system isolates core business logic from databases and web frameworks, facilitating elite testability and scalability.

---

## 🏗️ Architectural Blueprint

The codebase enforces a unidirectional dependency flow pointing **inward** toward the pure domain model. Infrastructure components (Web APIs, Databases, Message Brokers) are plugged in via interfaces (Ports).

```mermaid
graph TD
    %% Inbound Adapters (Driving)
    subgraph Inbound Adapters [Inbound Adapters / Driving]
        API[FastAPI REST API]
        gRPC[gRPC Controllers]
        CLI[Worker CLI]
    end

    %% Ports
    subgraph Ports [Ports / Contracts]
        IPorts[Inbound Ports / Use Cases]
        OPorts[Outbound Ports / SPIs]
    end

    %% Core Domain
    subgraph Core Domain [Core Domain & Business Logic]
        Services[Use Case Services]
        Entities[Domain Entities / Node, Task, TelemetryMetric]
        Exceptions[Domain Exceptions]
    end

    %% Outbound Adapters (Driven)
    subgraph Outbound Adapters [Outbound Adapters / Driven]
        DB[PostgreSQL DB Adapter]
        TS[InfluxDB / TimescaleDB Telemetry]
        Events[Kafka / Redis Event Publisher]
    end

    %% Dependency Arrows
    API --> IPorts
    gRPC --> IPorts
    CLI --> IPorts
    
    IPorts --> Services
    Services --> Entities
    Services --> Exceptions
    
    Services --> OPorts
    
    OPorts --> DB
    OPorts --> TS
    OPorts --> Events

    %% Styling
    style Core Domain fill:#76b900,stroke:#5c8f00,stroke-width:2px,color:#fff
    style Ports fill:#0277bd,stroke:#01579b,stroke-width:2px,color:#fff
    style Inbound Adapters fill:#37474f,stroke:#263238,stroke-width:2px,color:#fff
    style Outbound Adapters fill:#37474f,stroke:#263238,stroke-width:2px,color:#fff
```

---

## ✨ Key Technical Highlights

### 1. Pure Domain Isolation
No ORM annotations (`SQLAlchemy`, `Django`) or framework decorators (`FastAPI`) touch the domain models. The domain is pure Python 3.12. This ensures that the core business logic remains unaffected by framework upgrades or changes in the infrastructure layer.

### 2. Immutable State Transitions
Entities are modeled using `@dataclass(frozen=True)`. State transitions return new mutated instances, eliminating side effects and enhancing safety against race conditions in concurrent execution environments:
```python
# State transition returning a new copy of the Node
def update_heartbeat(self, timestamp: datetime) -> "Node":
    return replace(self, last_heartbeat=timestamp, status=NodeStatus.ONLINE)
```

### 3. Reproducible Environments with Flox
All system dependencies (Python 3.12, PostgreSQL 16, Redis) are managed declaratively in `.flox/env/manifest.toml`. Developers can initialize the complete workspace, compile dependencies, and spin up sandboxed database services locally with a single command, avoiding local machine pollution.

### 4. Task Idempotency & Concurrency Safety
Built-in mechanisms to handle network retries gracefully using client-provided idempotency keys. If a task creation request is duplicated, the system returns the existing task without altering the database state.

### 5. High-Frequency Telemetry Ingestion
Clean contracts and database models designed for high-frequency telemetry streaming (CPU, GPU, and Temperature metrics) from remote nodes.

---

## 📂 Project Structure

```text
.
├── .flox/                      # Declarative Nix-based virtual environments
│   └── env/
│       └── manifest.toml       # Environment packages (Postgres, Redis, Python, uv)
├── cmd/
│   └── api/
│       └── main.py             # Entrypoint & FastAPI setup (global exception handling)
├── src/
│   ├── core/                   # 🛑 Pure Domain - NO FRAMEWORKS
│   │   ├── domain/             # Entities, Value Objects, Domain Exceptions
│   │   ├── ports/              # Inbound & Outbound Interfaces (contracts)
│   │   └── use_cases/          # Business logic services (Use Cases)
│   ├── adapters/               # 🔌 Infrastructure & Adapters (Web, DB, Redis)
│   │   ├── inbound/            # Pydantic schemas and FastAPI routers
│   │   └── outbound/           # SQLAlchemy 2.0 ORM models & Async repositories
│   └── config/                 # Dependency injection setup
├── tests/
│   ├── unit/                   # High-speed unit tests (no databases required, uses Fakes)
│   └── integration/            # Test adapters against real Postgres/Redis inside Flox
├── .gitignore
├── LICENSE
├── requirements.txt
└── README.md
```

---

## 🛠️ API Reference

All requests/responses are mapped to strict Pydantic schemas. Custom domain exceptions are caught by global handlers and mapped to standard HTTP status codes.

| Method | Endpoint | Description | Payload | Success | Errors |
|:---|:---|:---|:---|:---|:---|
| **POST** | `/v1/nodes` | Register a new worker node | `{"hostname": "str", "hardware_specs": {}}` | `201 Created` | `409 Conflict` (Duplicate) |
| **POST** | `/v1/nodes/{id}/heartbeat` | Report node heartbeat (keepalive) | None | `204 No Content` | `404 Not Found` |
| **POST** | `/v1/nodes/{id}/telemetry` | Ingest node metrics | `{"cpu_usage": float, "gpu_usage": float, "temperature": float}` | `201 Created` | `404 Not Found`, `400 Bad Request` |
| **POST** | `/v1/tasks` | Create a task (Idempotent) | `{"idempotency_key": "str", "payload": {}}` | `201 Created` | `400 Bad Request` |
| **POST** | `/v1/tasks/{id}/dispatch` | Assign task to an online node | Query: `?node_id=str` | `200 OK` | `404 Not Found`, `409 Conflict` (Node Offline) |
| **POST** | `/v1/tasks/{id}/transition` | Transition task execution status | Query: `?target_status=str` | `200 OK` | `404 Not Found`, `409 Conflict` (Invalid State) |
| **GET** | `/health` | API Health check | None | `200 OK` | None |

---

## 🚀 Quick Start (via Flox)

1. **Install Flox**:
   Follow the official instructions at [flox.dev](https://flox.dev/docs/install-flox/install/).

2. **Clone and Enter Environment**:
   ```bash
   git clone https://github.com/Casta2007-ccs/gpu-fleet-commander.git
   cd gpu-fleet-commander
   flox activate --start-services
   ```
   *This installs Python 3.12, PostgreSQL, Redis, sets up a clean virtual environment using `uv`, and boots database background services locally inside a user-space sandbox.*

3. **Database Local Setup** (within Flox environment):
   ```bash
   db-init    # Initialize database files
   db-start   # Start local PostgreSQL service
   db-create  # Create 'gpu_fleet' database
   ```

4. **Verify Installation**:
   ```bash
   run-tests
   ```

---

## 🧪 Testing & Code Quality

Prerequisites: A virtual environment with dependencies installed (handled automatically on `flox activate`).

* **Run Unit Tests (In-Memory)**:
  Runs 13 tests checking domain validation, exceptions, and idempotency logic. Executed via mock doubles in less than 50ms:
  ```bash
  python -m pytest tests/unit/
  ```

---

## 💡 Technical Decisions & Architectural Context

### Why Hexagonal Architecture?
In enterprise systems, infrastructure changes frequently. By structuring this control plane with clear **Inbound** and **Outbound** ports:
- We can swap the PostgreSQL database for a time-series database (e.g., InfluxDB or TimescaleDB) to handle millions of telemetry records, **without modifying a single line of business logic** in the core.
- We can transition from a REST API to a gRPC or GraphQL interface by simply writing a new Inbound Adapter.

### Why Async SQLAlchemy 2.0 & Python 3.12 Dataclasses?
- **Concurrency**: Distributed worker node communication requires high-performance non-blocking I/O. Async/Await prevents the thread-pool starvation common in synchronous Python architectures.
- **Strict Typing**: Python 3.12 typed dataclasses with `__post_init__` checks ensure that corrupt payloads cannot penetrate the domain boundary.

---

## 📄 License

This project is licensed under the terms of the MIT License. See [LICENSE](LICENSE) for details.
