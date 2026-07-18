# Architecture and Roadmap: Distributed Fleet Control Plane

## 1. System Overview
This project serves as a lightweight Control Plane for managing a distributed fleet of worker nodes. It handles node registration, heartbeat telemetry monitoring, and idempotent task dispatching. The system is designed following strict **Hexagonal Architecture (Ports and Adapters)** principles.

Environment reproducibility is guaranteed across all operating systems (Linux, macOS, Windows) using **Flox**, ensuring a frictionless Developer Experience (DX).

---

## 2. Core Domain & Contracts (Hexagonal Architecture)

The system is strictly divided into the **Core** (Business Logic) and **Adapters** (Infrastructure/Delivery). The Core contains zero external dependencies (no ORMs, no web frameworks).

### 2.1 Domain Entities
Pure data structures and business rules.
- **`Node`**: Represents a physical or virtual worker. 
  - *Attributes*: `id`, `hostname`, `status` (ONLINE/OFFLINE), `hardware_specs`, `last_heartbeat`.
- **`Task`**: A unit of work dispatched to a Node.
  - *Attributes*: `id`, `node_id`, `payload`, `status` (PENDING/RUNNING/COMPLETED/FAILED), `retries`.
- **`TelemetryMetric`**: Time-series data points from nodes.
  - *Attributes*: `node_id`, `timestamp`, `cpu_usage`, `gpu_usage`, `temperature`.

### 2.2 Ports (Interfaces)
Contracts defining how the Core interacts with the outside world.

**Inbound Ports (Driving / Use Cases):**
- `INodeProvisioningUseCase`: Handles node registration and lifecycle.
- `ITaskOrchestratorUseCase`: Dispatches tasks and handles task acknowledgments idempotently.
- `ITelemetryIngestionUseCase`: Processes incoming heartbeat and metrics data.

**Outbound Ports (Driven / SPIs):**
- `INodeRepository`: Interface for Node persistence.
- `ITaskRepository`: Interface for Task persistence and transactional locking.
- `ITelemetryRepository`: Interface for time-series data storage.
- `IEventPublisher`: Interface for emitting domain events (e.g., `NodeOfflineEvent`, `TaskFailedEvent`).

---

## 3. Directory Structure

The repository is structured to enforce the dependency rule: dependencies point **inward** toward the core.

```text
.
├── .flox/                      # Declarative, reproducible environments (Postgres, Python/Java, Redis)
├── cmd/                        # Application entry points
│   └── api/                    # Main application bootstrap and DI wiring
├── src/
│   ├── core/                   # 🛑 PURE DOMAIN - NO FRAMEWORKS ALLOWED
│   │   ├── domain/             # Entities, Value Objects, Domain Exceptions
│   │   ├── ports/              # Inbound & Outbound Interfaces
│   │   └── use_cases/          # Application services implementing Inbound Ports
│   ├── adapters/               # 🔌 INFRASTRUCTURE
│   │   ├── inbound/            # REST API Controllers (FastAPI/Spring), gRPC handlers
│   │   └── outbound/           # SQL Repositories (SQLAlchemy/Hibernate), Message Brokers
│   └── config/                 # Dependency Injection container setup
├── tests/
│   ├── unit/                   # Blazing fast core tests (mocked outbound ports)
│   ├── integration/            # Adapter tests hitting real DBs inside Flox env
│   └── e2e/                    # Full API black-box testing
├── docs/
│   └── openapi.yaml            # Strict API contracts (API-First Design)
└── ARCHITECTURE_AND_ROADMAP.md
```

---

## 4. API Design Standards
- **Idempotency**: All `POST` requests for task dispatching will require an `Idempotency-Key` header to prevent duplicate execution during network retries.
- **Pagination**: Collection endpoints (`/v1/nodes`, `/v1/tasks`) implement cursor-based pagination.
- **Graceful Error Handling**: Standardized RFC 7807 Problem Details for HTTP APIs (`application/problem+json`).

---

## 5. Public Roadmap

### Phase 1: MVP Backend & Core Domain (Weeks 1-2)
*Goal: Establish the reproducible foundation and pure business logic.*
- [x] Define the **Flox environment** (`manifest.toml`) pinning the language runtime and build tools.
- [x] Implement Domain Entities and Use Cases in the `src/core/` directory.
- [ ] Achieve 100% unit test coverage in the core using in-memory mock repositories.
- [ ] Design the `openapi.yaml` contract for the REST API.

### Phase 2: Infrastructure & Database Integration (Weeks 3-4)
*Goal: Plug the adapters into the core.*
- [ ] Spin up PostgreSQL locally via Flox services.
- [x] Implement the SQL Outbound Adapters (Repositories) using the chosen database driver/ORM.
- [ ] Implement the REST API Inbound Adapters implementing the OpenAPI contract.
- [ ] Write integration tests for database adapters using Testcontainers or Flox temporary databases.
- [ ] Wire up Dependency Injection in the entry point.

### Phase 3: Cross-Platform UI & Telemetry Dashboard (Weeks 5-6)
*Goal: Visualize the system at scale.*
- [ ] Create a lightweight cross-platform dashboard (e.g., React/TypeScript or a native desktop app).
- [ ] Implement real-time telemetry streaming (Server-Sent Events or WebSockets) via the API adapter.
- [ ] Add a simulated CLI worker (`cmd/worker`) that registers itself, receives tasks, and reports fake hardware metrics to showcase the end-to-end flow.
- [ ] Finalize documentation, architecture diagrams, and deployment instructions.
