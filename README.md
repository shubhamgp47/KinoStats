# KinoStats: Dual-Stack Letterboxd Analytics & Completion Engine

[![Java](https://img.shields.io/badge/Java-21%20LTS-orange.svg)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3+-green.svg)](https://spring.io/projects/spring-boot)
[![Python](https://img.shields.io/badge/Python-3.12%2B%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-teal.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B%20%7C%20Vite-cyan.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)

KinoStats is a multi-tenant cinema analytics platform that provide users statistics based on their latterboxd profile. Users can drop raw Letterboxd export files (`.zip` or `.csv`) into the client without authentication and instantly receive deep viewing metrics, interactive genre distributions, and canonical director filmography completion visualization.

We have created **Dual-Backend Architectural Parity**: the backend is implemented in **Java 21 (Spring Boot 3)** using Project Loom Virtual Threads, and in modern **Python 3.12+ (FastAPI)** using AsyncIO and SQLAlchemy 2.0. Both backends work with identical REST API specification and connect to the PostgreSQL schema, allowing a decoupled React client to switch backends with zero code changes.

---

## Architecture Overview

```
                      ┌───────────────────────────────────────┐
                      │            React Frontend             │
                      │ (Vite + TS)                           │
                      └───────────────────┬───────────────────┘
                                          │
                        VITE_API_BASE_URL (Toggle in .env)
                         :8080 (Java) ◄───┴───► :8000 (Python)
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌───────────────────────────────┐               ┌───────────────────────────────┐
   │      Java 21 / Spring Boot 3  │               │      Python 3.12+ / FastAPI   │
   │  - Virtual Threads (Loom)     │               │  - AsyncIO Event Loop         │
   │  - RestClient + Semaphore(10) │               │  - httpx + Async Semaphore    │
   │  - Spring Data JPA (Hibernate)│               │  - SQLAlchemy 2.0 (asyncpg)   │
   │  - Flyway Migrations          │               │  - Alembic Migrations         │
   │  - Records + Jakarta Validate │               │  - Pydantic v2 Schemas        │
   └──────────────┬────────────────┘               └──────────────┬────────────────┘
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          ▼
                      ┌───────────────────────────────────────┐
                      │        PostgreSQL 16 Database         │
                      │  - Shared Cache: movies, genres, dirs │
                      │  - Tenant Logs: watch_logs, users     │
                      └───────────────────────────────────────┘
```

---



## Dual-Stack Cross-Comparison Reference

| Architectural Layer | Java Implementation | Python Implementation | Frontend & Tooling |
| :--- | :--- | :--- | :--- |
| **Language & Runtime** | Java 21 LTS | Python 3.12+ / 3.13 (`venv` + `pip-tools`) | Node 20+, TypeScript 5.x |
| **Web Framework** | Spring Boot 3.3+ (Spring Web) | FastAPI 0.111+ (ASGI: Uvicorn) | React 18+ (Vite) |
| **Persistence / ORM** | Spring Data JPA (Hibernate 6) | SQLAlchemy 2.0 (`asyncpg`) | TanStack React Query v5 |
| **Migrations** | Flyway (`V1`, `V2` SQL scripts) | Alembic (Async migrations) | N/A |
| **Validation / DTO** | Java 21 Records + Jakarta | Pydantic v2 (`pydantic-core` / Rust) | Zod / TypeScript Interfaces |
| **HTTP Client** | Spring `RestClient` | `httpx.AsyncClient` | Axios |
| **Concurrency** | Loom Virtual Threads (`Thread.ofVirtual`) | Single-Threaded `asyncio` Event Loop | Web Workers / Browser Async |
| **Database Pool** | HikariCP (`pool-size=10`) | SQLAlchemy `AsyncEngine` (`QueuePool`) | N/A |
| **Rate Throttling** | `java.util.concurrent.Semaphore` | `asyncio.Semaphore` | Client-side Debounce |
| **Primary Database** | PostgreSQL 16 Alpine | PostgreSQL 16 Alpine | LocalStorage (Session Cache) |

---

## Directory Structure

```plaintext
kinostats/
├── docker-compose.yml              # Local infrastructure (PostgreSQL 16 & Redis 7)
├── backend-java/                   # Enterprise Java Stack
│   ├── pom.xml                     # Maven project descriptor
│   └── src/
│       ├── main/
│       │   ├── java/com/cinestats/backend_java/
│       │   │   ├── controller/     # ImportController, StatsController
│       │   │   ├── dto/            # Records for Requests, Responses, and TMDB schemas
│       │   │   ├── model/          # JPA Entities: User, Movie, Genre, Director, WatchLog
│       │   │   ├── repository/     # Spring Data Repositories & Native SQL Projections
│       │   │   └── service/        # IngestionService, TmdbService, StatsService
│       │   └── resources/
│       │       ├── application.yml
│       │       └── db/migration/   # V1__init_schema.sql, V2__add_director_total_directed.sql
│       └── test/                   # JUnit 5 & Integration Tests
├── backend-python/                 # Asynchronous Python Stack
│   ├── requirements.in             # Top-level dependencies declaration
│   ├── requirements.txt            # Locked, deterministic dependencies snapshot
│   └── src/
│       ├── api/
│       │   ├── deps.py             # FastAPI session dependencies (get_current_user, get_db)
│       │   └── v1/endpoints/       # imports.py, stats.py
│       ├── core/                   # config.py (Pydantic Settings), database.py (AsyncEngine)
│       ├── models/                 # SQLAlchemy 2.0 Declarative Models
│       ├── schemas/                # Pydantic v2 DTOs (Request / Response validation)
│       ├── services/               # ingestion.py, tmdb_client.py, stats_engine.py
│       └── main.py                 # ASGI entrypoint & Lifespan context manager
└── frontend/                       # Decoupled React Client
    ├── src/
    │   ├── components/             # MetricCard, DirectorGauges, GenreChart (Recharts)
    │   ├── features/               # upload/ (JSZip & PapaParse), dashboard/ (useStats hooks)
    │   ├── services/api.ts         # Axios client reading import.meta.env.VITE_API_BASE_URL
    │   └── App.tsx                 # Root session state machine
    ├── .env.development           # Dynamic API host config (port 8080 vs 8000)
    └── package.json
```

---



## Getting Started

### 1. Prerequisites
* **Docker & Docker Compose** (for PostgreSQL 16 & Redis 7)
* **Java 21 LTS** & **Maven 3.9+**
* **Python 3.12+** or **3.13**
* **Node.js 20+** & **npm**
* A valid **TMDB Read Access Token (API v4)**

### 2. Infrastructure Boot
From the project root:
```bash
docker compose up -d
```
Verify PostgreSQL is healthy:
```bash
docker exec -it kinostats-pg psql -U cinema -d kinostats -c "\dt"
```

---

### 3. Running the Java 21 Backend (Port 8080)
1. Add your TMDB credentials in `backend-java/src/main/resources/application.yml`:
   ```yaml
   tmdb:
     api-key: "YOUR_TMDB_BEARER_TOKEN"
     api-url: "https://api.themoviedb.org/3"
   ```
2. Compile and start Spring Boot (Flyway automatically runs all migrations):
   ```bash
   cd backend-java
   ./mvnw clean spring-boot:run
   ```
3. Test Health: `http://localhost:8080/actuator/health` or Swagger at `http://localhost:8080/swagger-ui.html`.

---

### 4. Running the Python Backend (Port 8000)
1. Create and activate a dedicated virtual environment:
   ```bash
   cd backend-python
   python -m venv .venv
   
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # macOS / Linux
   source .venv/bin/activate
   ```
2. Install pinned dependencies via `pip-tools`:
   ```bash
   python -m pip install --upgrade pip pip-tools
   pip-sync requirements.txt
   ```
3. Create a `.env` file inside `backend-python/`:
   ```env
   POSTGRES_USER=cinema
   POSTGRES_PASSWORD=secretpassword
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=kinostats
   TMDB_API_KEY=YOUR_TMDB_BEARER_TOKEN
   ```
4. Start the ASGI server:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```
5. Test Health & Interactive Docs: `http://localhost:8000/docs`.

---

### 5. Running the Frontend
1. Navigate to the client directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Configure the target backend in `frontend/.env.development`:
   ```bash
   # Point to Java Spring Boot
   VITE_API_BASE_URL=http://localhost:8080

   # OR Point to Python FastAPI
   # VITE_API_BASE_URL=http://localhost:8000
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:5173` and upload your Letterboxd `.zip` archive or `diary.csv`.

