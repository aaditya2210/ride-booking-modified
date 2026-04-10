# RideBook

<div align="center">

![Architecture](https://img.shields.io/badge/architecture-microservices-2563eb?style=for-the-badge)
![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20gRPC-059669?style=for-the-badge)
![Frontend](https://img.shields.io/badge/frontend-React%2018-0ea5e9?style=for-the-badge)
![Infra](https://img.shields.io/badge/infra-Docker%20Compose-1d4ed8?style=for-the-badge&logo=docker&logoColor=white)
![Observability](https://img.shields.io/badge/observability-Prometheus%20%2B%20Grafana-f97316?style=for-the-badge)

A distributed ride-booking platform built to demonstrate a practical microservices architecture with REST, gRPC, WebSockets, polyglot persistence, circuit breakers, and end-to-end observability.

</div>

## Overview

RideBook models the core workflow of a cab booking system:

- users can be created and managed
- drivers are stored independently and exposed through REST and gRPC
- rides are matched through a dedicated orchestration service
- fares are calculated by a pricing service
- payments are validated and finalized through a separate payment service
- notifications are persisted in MongoDB and pushed over WebSockets

The repository is structured as a multi-service system behind an NGINX gateway. The frontend talks only to the gateway, while internal service-to-service communication uses gRPC and HTTP where appropriate.

## Highlights

- Microservices split by business capability: user, driver, ride matching, pricing, payment, notification
- API gateway with centralized routing through NGINX
- REST for north-south traffic and gRPC for internal synchronous calls
- Polyglot persistence:
  - MySQL for users and payments
  - MongoDB for drivers and notifications
  - Redis for ride state and pricing cache
- Real-time notification delivery using WebSockets
- Prometheus metrics on every service and a pre-provisioned Grafana dashboard
- Circuit breaker protection in ride matching and payment service integrations
- Full local environment with Docker Compose and service GUI tools

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

| Service | Main responsibility | Storage | External interface |
| --- | --- | --- | --- |
| `user-service` | Rider CRUD | MySQL | REST |
| `driver-service` | Driver CRUD, availability, assignment, release | MongoDB | REST + gRPC |
| `ride-matching-service` | Create and manage rides, orchestrate match flow | Redis | REST + gRPC |
| `pricing-service` | Fare and surge calculation, short-lived caching | Redis | REST + gRPC |
| `payment-service` | Payment processing, ride validation, driver release | MySQL | REST |
| `notification-service` | Notification persistence and live delivery | MongoDB | REST + WebSocket |
| `frontend` | Operator/demo UI | none | Browser app |
| `nginx` | Gateway and reverse proxy | none | HTTP entry point |

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
    R->>RR: Store ride snapshot with TTL
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
| Cache / ephemeral state | Redis 7 |
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

### Run the Full System

```bash
docker compose up --build
```

Once the stack is healthy, open:

| Component | URL |
| --- | --- |
| Application / Gateway | `http://localhost:8080` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| phpMyAdmin | `http://localhost:9001` |
| Mongo Express `driver-db` | `http://localhost:9002` |
| Mongo Express `notification-db` | `http://localhost:9003` |
| RedisInsight | `http://localhost:9004` |

### Default GUI Credentials

| Tool | Username | Password |
| --- | --- | --- |
| Grafana | `admin` | `admin` |
| Mongo Express | `admin` | `admin123` |
| phpMyAdmin | `root` | `password` |

## API Surface

The gateway exposes the main application routes:

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

Open a WebSocket connection:

```text
ws://localhost:8080/ws
ws://localhost:8080/ws/1
```

## Internal Contracts

The protocol buffer definition in `proto/ride.proto` defines three gRPC services:

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

- request count, latency, and in-flight request gauges
- circuit breaker state, transitions, and call outcomes
- active notification WebSocket connections

### Circuit Breakers

Circuit breakers are implemented in shared code and currently protect downstream calls in:

- `ride-matching-service`
  - `driver-service-grpc`
  - `pricing-service-grpc`
- `payment-service`
  - ride validation, ride lookup, ride update
  - driver release
  - notification delivery

Operational snapshots are available at:

- `/circuit-breakers` on `ride-matching-service`
- `/circuit-breakers` on `payment-service`

## Development Notes

- The services bootstrap their schemas or seed data on startup.
- Ride records are stored in Redis with a one-hour TTL.
- Pricing responses are cached briefly in Redis.
- The current implementation is optimized for local demonstration and academic architecture study rather than production-grade security or cloud deployment.

## Why This Repo Is Useful

RideBook is a compact reference implementation for learning how multiple backend services interact in a realistic workflow. It is especially useful for understanding:

- service decomposition and data ownership
- gateway-based routing
- REST plus gRPC hybrid communication
- live notifications with WebSockets
- observability in distributed systems
- resilience patterns such as circuit breakers

## License

This repository does not currently include a license file. Add one if you intend to distribute or reuse the project outside its current academic context.
