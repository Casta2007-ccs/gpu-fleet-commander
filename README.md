# ⚡ GPU Fleet Commander ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Reproducible Env: Flox](https://img.shields.io/badge/environment-Flox-orange.svg)](https://flox.dev/)
[![Architecture: Hexagonal](https://img.shields.io/badge/architecture-Hexagonal-green.svg)](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))

**GPU Fleet Commander** is a lightweight, high-performance Control Plane designed for orchestrating distributed computing nodes (such as server clusters or NVIDIA Jetson edge systems). It handles real-time node registration, heartbeat telemetry monitoring, and idempotent task dispatching.

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
    style Core Domain fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#fff
    style Ports fill:#0277bd,stroke:#01579b,stroke-width:2px,color:#fff
    style Inbound Adapters fill:#37474f,stroke:#263238,stroke-width:2px,color:#fff
    style Outbound Adapters fill:#37474f,stroke:#263238,stroke-width:2px,color:#fff
```

---

## ✨ Key Technical Highlights

- **Pure Domain Isolation**: No ORM annotations (`SQLAlchemy`, `Django`) or framework decorators (`FastAPI`) touch the domain models. The domain is pure Python 3.12.
- **Immutable State Transitions**: Entities are modeled using `@dataclass(frozen=True)`. State transitions return new mutated instances, eliminating side effects and enhancing race-condition safety.
- **Reproducible Environments with Flox**: All system dependencies (Python 3.12, PostgreSQL 16, Redis) are managed declaratively in a `.flox/env/manifest.toml`. Developers can initialize the complete workspace with one command.
- **Task Idempotency**: Built-in mechanisms to handle network retries gracefully using client-provided idempotency keys.
- **Telemetry Ingestion**: Clean contracts designed for high-frequency telemetry streaming (CPU, GPU, Temperature metrics).

---

## 📂 Project Structure

```text
.
├── .flox/                      # Declarative Nix-based virtual environments
│   └── env/
│       └── manifest.toml       # Environment packages (Postgres, Redis, Python, uv)
├── src/
│   ├── core/                   # 🛑 Pure Domain - No frameworks allowed
│   │   ├── domain/             # Entities, Value Objects, Domain Exceptions
│   │   ├── ports/              # Inbound & Outbound Interfaces (contracts)
│   │   └── use_cases/          # Business logic services
│   ├── adapters/               # 🔌 Infrastructure & Adapters (Web, DB, Redis)
│   │   ├── inbound/
│   │   └── outbound/
│   └── config/                 # Dependency injection setup
├── tests/
│   ├── unit/                   # High-speed unit tests (no databases required)
│   └── integration/            # Test adapters against real Postgres/Redis inside Flox
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start (via Flox)

1. **Install Flox** if you haven't already:
   Follow the official instructions at [flox.dev](https://flox.dev/docs/install-flox/install/).

2. **Clone and Enter Environment**:
   ```bash
   git clone https://github.com/Casta2007-ccs/gpu-fleet-commander.git
   cd gpu-fleet-commander
   flox activate --start-services
   ```
   *This command installs Python 3.12, PostgreSQL, Redis, sets up a clean virtual environment using `uv`, and boots database background services locally inside a user-space sandbox.*

3. **Verify Installation**:
   ```bash
   run-tests
   ```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
