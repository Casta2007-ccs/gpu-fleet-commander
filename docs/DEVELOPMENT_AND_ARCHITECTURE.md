# 📖 Development & Architecture Guide: GPU Fleet Commander

This document provides an exhaustive, production-grade guide to the architectural patterns, software engineering decisions, and setup procedures implemented in the **GPU Fleet Commander** control plane. It serves as both an onboarding guide and a technical design document.

---

## 🛠️ 1. Architectural Philosophy: Hexagonal (Ports & Adapters)

In enterprise infrastructure systems, frameworks and databases are details that change. The core business rules of our control plane (how worker nodes are registered, how heartbeats are processed, and how tasks are dispatched) should not be coupled to web servers or database drivers.

We follow **Hexagonal Architecture** to enforce a strict boundary between the core logic and the outside world.

```
       +-------------------------------------------------------+
       |                     Infrastructure                    |
       |                                                       |
       |     +-------------------------------------------+     |
       |     |                 Use Cases                 |     |
       |     |                                           |     |
       |     |     +-------------------------------+     |     |
       |     |     |          Core Domain          |     |     |
       |     |     |                               |     |     |
       |     |     |    - Node / Task Entities     |     |     |
       |     |     |    - Domain Exceptions        |     |     |
       |     |     +-------------------------------+     |     |
       |     |                                           |     |
       |     |    - NodeProvisioningService              |     |
       |     |    - TaskOrchestratorService              |     |
       |     +-------------------------------------------+     |
       |                           |                           |
       |     - FastAPI Routers     |     - Async Repositories  |
       |     - Pydantic Schemas    |     - ORM Models          |
       |     - Worker CLI          |     - Event Publisher     |
       |                                                       |
       +-------------------------------------------------------+
```

### Dependency Rule
All source code dependencies point **inward** toward the Core Domain. The core domain does not import anything from `sqlalchemy`, `pydantic`, or `fastapi`.

---

## 🧠 2. Core Domain Layer (`src/core/domain/`)

The Core Domain contains the business entities and validation rules.

### 2.1 Domain Entities (`entities.py`)
Domain models are defined using Python 3.12 `@dataclass(frozen=True)` to enforce **immutability**:
* **Functional State Transitions**: Because the dataclasses are frozen, state transitions do not modify the entity in place. Instead, they return a new instance via `dataclasses.replace`. This eliminates side effects and side-channel state modifications during concurrent operations.
* **Strict Validation**: Type validation and range boundaries are checked during instantiation in the `__post_init__` hook. If invalid parameters are passed, a `ValueError` or `TypeError` is raised instantly.

```python
# Transitioning status in a frozen dataclass
def assign_to_node(self, node_id: str) -> "Task":
    if self.status != TaskStatus.PENDING:
        raise InvalidTaskStateException(...)
    return replace(self, node_id=node_id, status=TaskStatus.RUNNING)
```

### 2.2 Domain Exceptions (`exceptions.py`)
We define custom, domain-specific exceptions inheriting from a base `DomainException`. 
* **Why not use HTTP exceptions?** Exposing HTTP codes (like `HTTPException(status_code=404)`) inside the domain couples the core business logic to the Web layer.
* **Separation of Concerns**: The core raises exceptions like `NodeNotFoundError` or `InvalidTaskStateException`. The inbound REST adapter (FastAPI) handles the conversion from these domain exceptions to HTTP status codes at the application edge.

---

## 🔌 3. Ports Layer (`src/core/ports/interfaces.py`)

Ports act as boundary contracts.

### 3.1 Inbound Ports (Driving / Use Cases)
Defined as Abstract Base Classes (`abc.ABC`), Inbound Ports declare what operations the core can perform. Inbound Adapters (like `routers.py`) trigger these use cases.
* **`INodeProvisioningUseCase`**: Handles node registration and activity latidos.
* **`ITaskOrchestratorUseCase`**: Manages task creation, distribution, and status transitions.
* **`ITelemetryIngestionUseCase`**: Ingests metrics reporting.

### 3.2 Outbound Ports (Driven / SPIs)
Outbound Ports define what the core needs from external systems (databases, publishers). Outbound Adapters implement these interfaces.
* **`INodeRepository` / `ITaskRepository` / `ITelemetryRepository`**: Abstract persistence.
* **`IEventPublisher`**: Abstract messaging interface to notify external services when domain events occur.

*Note: All port methods are declared as `async def` to support modern, non-blocking asynchronous event loops.*

---

## 💾 4. Outbound Adapters: Persistence (`src/adapters/outbound/`)

Outbound Adapters implement the Outbound Ports using concrete technologies.

### 4.1 Database Engine (`database.py`)
Configures the connection to PostgreSQL:
* **Async Engine**: Uses `create_async_engine` with the `asyncpg` driver to prevent database I/O from blocking Python's single-threaded event loop.
* **Connection Pool Protection**: Enabled `pool_pre_ping=True` to run a health test (`SELECT 1`) on checked-out connections, automatically recovering from disconnected database sockets.
* **Transaction Lifecycle**: The `get_db_session` async generator yields a request-scoped session, performing an automatic `commit()` if successful, or `rollback()` if any error occurs.

### 4.2 ORM Models (`orm_models.py`)
Mapea las tablas SQL usando la sintaxis declarativa moderna de SQLAlchemy 2.0:
* **JSON Mapping**: Node hardware specifications and task payloads are mapped to `JSON` columns, allowing structured metadata (like GPU specs or container job arguments) to be saved without rigid schema migrations.
* **Enum Columns**: State values (`ONLINE`, `RUNNING`, etc.) are mapped to database-level enums using `sqlalchemy.Enum(native_enum=False)` for maximum compatibility across databases.

### 4.3 Async Repositories (`sql_repositories.py`)
Concrete implementations of the outbound ports using SQLAlchemy's async API:
* **Domain Mapping**: The repository queries the database returning `ORM` models, but maps them back to pure, immutable domain entities using constructor arguments before returning them to the core services. ORM models never leave the repository layer.
```python
# Database ORM instance mapped to Domain Entity
return Node(
    id=db_node.id,
    hostname=db_node.hostname,
    status=db_node.status,
    hardware_specs=db_node.hardware_specs,
    last_heartbeat=db_node.last_heartbeat
)
```

---

## 🌐 5. Inbound Adapters: REST API (`src/adapters/inbound/`)

Inbound Adapters translate network requests into core operations.

### 5.1 API Schemas (`api_schemas.py`)
Uses **Pydantic v2** models to validate incoming JSON payloads and format outgoing responses. This serves as our Data Transfer Object (DTO) layer, shielding internal domain attributes from the public API schema.

### 5.2 Routers (`routers.py`)
Maps HTTP requests to use cases.
* **Request-Scoped Dependency Injection**: We use FastAPI's `Depends()` to instantiate services on the fly. The dependencies instantiate repositories with the active request-scoped database session, inject them into the services, and return the use-case service to the endpoint.

```python
async def get_node_service(session: AsyncSession = Depends(get_db_session)) -> NodeProvisioningService:
    node_repo = SqlAsyncNodeRepository(session)
    event_publisher = LoggingEventPublisher()
    return NodeProvisioningService(node_repo, event_publisher)
```

### 5.3 Application Entrypoint (`cmd/api/main.py`)
Initializes the FastAPI application and configures global middlewares:
* **Global Domain Exception Handlers**: Intercepts domain exceptions and maps them to clean REST error models (RFC 7807) to avoid disclosing internal stack traces (returning a standard 500 error):
  - `NodeNotFoundError` $\rightarrow$ `404 Not Found`
  - `DuplicateNodeError` $\rightarrow$ `409 Conflict`
  - `NodeOfflineException` $\rightarrow$ `409 Conflict`
  - `InvalidTaskStateException` $\rightarrow$ `409 Conflict`

---

## 📦 6. Reproducibility with Flox (`.flox/env/manifest.toml`)

To ensure that the development environment compiles and runs identically on Linux, macOS, and Windows WSL without manual toolchain setups, we use **Flox**.

### Packages Declared:
* `python312`: Strict language runtime.
* `uv`: High-performance Python package installer.
* `poetry`: Modern dependency manager.
* `postgresql_16`: Local sandboxed database service.
* `redis`: Local key-value store for event broker simulation.

### Service Activation:
When activating the environment using `flox activate --start-services`, Flox automatically boots local PostgreSQL and Redis servers in user space (no `sudo` required), binding them to ports `5432` and `6379` locally.

---

## 🧪 7. Testing Strategy

We follow a strict Test-Driven Development (TDD) workflow enabled by our decoupled ports.

### Unit Testing (`tests/unit/`)
Because use cases communicate via outbound interfaces, we do not require a live database to test business rules.
* **In-Memory Fakes (`fakes.py`)**: We implement in-memory versions of the repositories and publishers using standard Python dicts and lists.
* **Execution Speed**: Since there are no network, database, or disk I/O calls, the entire unit test suite runs in **less than 50ms**, enabling instant local feedback loops.
```bash
python -m pytest tests/unit/
```

---

## 🚀 8. Onboarding Checklist for Developers

1. **Verify environment tools**:
   Ensure `flox` is installed, then run `flox activate --start-services`.
2. **Bootstrap Database**:
   Run `db-init`, followed by `db-start`, then create the database using `db-create`.
3. **Install dependencies**:
   Run `uv pip install -r requirements.txt` (handled automatically on activation).
4. **Run unit tests**:
   Execute `python -m pytest tests/unit/`.
5. **Run the API server**:
   Execute `uvicorn cmd.api.main:app --reload --host 0.0.0.0 --port 8000`.
   Open the interactive API docs at `http://localhost:8000/docs`.
