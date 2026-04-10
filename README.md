# RideBook

<div align="center">

![Architecture](https://img.shields.io/badge/architecture-microservices-2563eb?style=for-the-badge)
![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20gRPC-059669?style=for-the-badge)
![Frontend](https://img.shields.io/badge/frontend-React%2018-0ea5e9?style=for-the-badge)
![Infra](https://img.shields.io/badge/infra-Docker%20Compose-1d4ed8?style=for-the-badge&logo=docker&logoColor=white)
![Observability](https://img.shields.io/badge/observability-Prometheus%20%2B%20Grafana-f97316?style=for-the-badge)

A distributed ride-booking platform that demonstrates a practical microservices architecture with REST, gRPC, WebSockets, polyglot persistence, circuit breakers, and end-to-end observability.

</div>

## Overview

RideBook models the core workflow of a cab booking platform:

- user onboarding and management
- driver onboarding and availability tracking
- ride request and driver assignment
- fare estimation
- payment processing
- notification persistence and real-time delivery

The frontend is exposed through an NGINX gateway, while backend services communicate through a mix of REST, gRPC, and WebSockets depending on the use case.

## Highlights

- Microservices split by business capability
- FastAPI-based backend services in Python
- React frontend dashboard
- gRPC for internal service communication
- MySQL, MongoDB, and Redis used according to data access patterns
- Prometheus metrics and Grafana dashboards included
- Circuit breaker protection for critical downstream calls
- Full local environment with Docker Compose

## Architecture

### High-Level System Diagram

```mermaid
flowchart LR
    subgraph Client["Client Layer"]
        Browser["Browser"]
        Frontend["React Frontend"]
        Browser --> Frontend
    end

    subgraph Edge["Edge Layer"]
        Gateway["NGINX API Gateway<br/>:8080"]
    end

    subgraph Services["Application Services"]
        User["User Service<br/>REST :8001"]
        Driver["Driver Service<br/>REST :8002<br/>gRPC :50052"]
        Ride["Ride Matching Service<br/>REST :8003<br/>gRPC :50051"]
        Pricing["Pricing Service<br/>REST :8006<br/>gRPC :50053"]
        Payment["Payment Service<br/>REST :8004"]
        Notify["Notification Service<br/>REST :8005<br/>WebSocket /ws"]
    end

    subgraph Data["Data Layer"]
        UserDB[("MySQL<br/>user-db")]
        PaymentDB[("MySQL<br/>payment-db")]
        DriverDB[("MongoDB<br/>driver-db")]
        NotifyDB[("MongoDB<br/>notification-db")]
        RideRedis[("Redis<br/>ride-redis")]
        PricingRedis[("Redis<br/>pricing-redis")]
    end

    subgraph Obs["Observability"]
        Prom["Prometheus"]
        Graf["Grafana"]
    end

    Frontend -->|HTTP / WebSocket| Gateway

    Gateway -->|REST| User
    Gateway -->|REST| Driver
    Gateway -->|REST| Ride
    Gateway -->|REST| Pricing
    Gateway -->|REST| Payment
    Gateway -->|REST + WS| Notify

    Ride -->|gRPC: get / assign driver| Driver
    Ride -->|gRPC: calculate fare| Pricing
    Payment -->|gRPC: validate / fetch / update ride| Ride
    Payment -->|gRPC: release driver| Driver
    Payment -->|HTTP: send notification| Notify

    User --> UserDB
    Driver --> DriverDB
    Ride --> RideRedis
    Pricing --> PricingRedis
    Payment --> PaymentDB
    Notify --> NotifyDB

    Prom -->|scrapes /metrics| User
    Prom -->|scrapes /metrics| Driver
    Prom -->|scrapes /metrics| Ride
    Prom -->|scrapes /metrics| Pricing
    Prom -->|scrapes /metrics| Payment
    Prom -->|scrapes /metrics| Notify
    Graf -->|queries| Prom
```

### Service Responsibilities

| Service | Responsibility | Storage | Interfaces |
| --- | --- | --- | --- |
| `user-service` | Rider CRUD | MySQL | REST |
| `driver-service` | Driver CRUD, availability, assignment, release | MongoDB | REST, gRPC |
| `ride-matching-service` | Ride creation and orchestration | Redis | REST, gRPC |
| `pricing-service` | Fare and surge calculation | Redis | REST, gRPC |
| `payment-service` | Payment processing and ride finalization | MySQL | REST |
| `notification-service` | Notification storage and live delivery | MongoDB | REST, WebSocket |
| `frontend` | Demo dashboard | None | Browser |
| `nginx` | Gateway and reverse proxy | None | HTTP |

## Flow Diagrams

### Ride Request Flow

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant G as NGINX Gateway
    participant R as Ride Matching Service
    participant D as Driver Service
    participant P as Pricing Service
    participant RR as Redis

    C->>G: POST /ride/request
    G->>R: Forward request
    R->>D: gRPC GetAvailableDrivers(limit=1)
    D-->>R: Available driver
    R->>D: gRPC AssignDriver(ride_id, driver_id)
    D-->>R: Assignment confirmed
    R->>P: gRPC CalculatePrice(pickup, dropoff, ride_type)
    P-->>R: Price response
    R->>RR: Store ride snapshot
    R-->>G: ride_id, driver, price, ETA
    G-->>C: Matched ride response
```

### Payment Completion Flow

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant G as NGINX Gateway
    participant Pay as Payment Service
    participant Ride as Ride Matching gRPC
    participant Driver as Driver gRPC
    participant DB as Payment DB
    participant Notify as Notification Service
    participant WS as WebSocket Client

    C->>G: POST /payments
    G->>Pay: Forward payment request
    Pay->>Ride: ValidateRide(ride_id, user_id, amount)
    Ride-->>Pay: Validation result + ride price
    Pay->>DB: Insert completed payment
    Pay->>Ride: UpdateRideStatus(ride_id, "paid")
    Pay->>Ride: GetRide(ride_id)
    Ride-->>Pay: ride with driver_id
    Pay->>Driver: ReleaseDriver(driver_id, ride_id)
    Pay->>Notify: POST /notify
    Notify-->>WS: Push notification event
    Pay-->>G: Payment success response
    G-->>C: Completed payment
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Axios |
| API / Services | FastAPI, Python 3 |
| Internal RPC | gRPC, Protocol Buffers |
| Gateway | NGINX |
| SQL storage | MySQL 8 |
| Document storage | MongoDB 7 |
| Cache / transient state | Redis 7 |
| Monitoring | Prometheus, Grafana |
| Local orchestration | Docker Compose |

## Repository Structure

```text
.
|-- frontend/
|-- nginx/
|-- proto/
|-- shared/
|-- user-service/
|-- driver-service/
|-- ride-matching-service/
|-- pricing-service/
|-- payment-service/
|-- notification-service/
|-- monitoring/
`-- docker-compose.yml
```

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Start the Stack

```bash
docker compose up -d --build
```

### Access Points

| Component | URL |
| --- | --- |
| Application / Gateway | `http://localhost:8080` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| phpMyAdmin | `http://localhost:9001` |
| Mongo Express `driver-db` | `http://localhost:9002` |
| Mongo Express `notification-db` | `http://localhost:9003` |
| RedisInsight | `http://localhost:9004` |

### Default Credentials

| Tool | Username | Password |
| --- | --- | --- |
| Grafana | `admin` | `admin` |
| Mongo Express | `admin` | `admin123` |
| phpMyAdmin | `root` | `password` |

## API Surface

The gateway exposes these main route groups:

| Capability | Route prefix |
| --- | --- |
| Users | `/users` |
| Drivers | `/drivers` |
| Ride management | `/ride`, `/rides` |
| Pricing | `/pricing` |
| Payments | `/payments` |
| Notifications | `/notifications`, `/notify`, `/ws` |
| Health checks | `/health`, `/health/users`, `/health/drivers`, `/health/rides`, `/health/payments`, `/health/notifications`, `/health/pricing` |

### Example Requests

Create a ride:

```bash
curl -X POST http://localhost:8080/ride/request \
  -H "Content-Type: application/json" \
  -d "{\"riderId\":1,\"pickup\":\"Campus\",\"dropoff\":\"Railway Station\",\"ride_type\":\"standard\"}"
```

Process a payment:

```bash
curl -X POST http://localhost:8080/payments \
  -H "Content-Type: application/json" \
  -d "{\"rideId\":\"ride-12345678\",\"userId\":1,\"amount\":25.0,\"payment_method\":\"card\"}"
```

WebSocket endpoints:

```text
ws://localhost:8080/ws
ws://localhost:8080/ws/1
```

## Internal Contracts

The protocol buffer definition in `proto/ride.proto` defines:

- `RideService`
  - `GetRide`
  - `ValidateRide`
  - `UpdateRideStatus`
- `DriverService`
  - `GetAvailableDrivers`
  - `AssignDriver`
  - `ReleaseDriver`
- `PricingService`
  - `CalculatePrice`

## Observability and Resilience

### Metrics

Each FastAPI service exposes Prometheus metrics at `/metrics`, including:

- HTTP request count and latency
- in-flight request gauges
- circuit breaker state and transition metrics
- notification WebSocket connection count

### Circuit Breakers

Circuit breakers are implemented in shared code and protect downstream calls in:

- `ride-matching-service`
  - driver lookup and assignment dependency
  - pricing dependency
- `payment-service`
  - ride validation, lookup, and update
  - driver release
  - notification delivery

Operational breaker snapshots are exposed by:

- `/circuit-breakers` on `ride-matching-service`
- `/circuit-breakers` on `payment-service`

## Development Notes

- Services bootstrap their own schema or seed data on startup.
- Ride data is stored in Redis with a one-hour TTL.
- Pricing responses are cached briefly in Redis.
- The current system is optimized for local demonstration and academic study rather than production deployment.

## License

This repository does not currently include a license file. Add one before publishing or redistributing the project externally.
