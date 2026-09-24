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
                      │  (Vite + TS + TanStack Query + Recharts) │
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

## Core System Patterns & Design Decisions

### 1. Database-First Lazy-Cache Pattern
Querying external APIs (such as TMDB) for hundreds or thousands of diary entries per user creates severe latency spikes and triggers downstream HTTP 429 errors.
* **On Ingestion**: The backend partitions incoming titles into **Cache Hits** and **Cache Misses** against PostgreSQL.
* **Cache Hits**: Bypasses external calls entirely, linking user logs to existing movie records in sub-second execution.
* **Cache Misses**: Resolved concurrently through rate-throttled workers against TMDB, then cached permanently for all users across the platform.

### 2. Guarding Downstream Rate Limits (The Thundering Herd)
* **Java**: Spawning hundreds of lightweight Virtual Threads (`Executors.newVirtualThreadPerTaskExecutor()`) without a governor floods TMDB. We protect external I/O using a `java.util.concurrent.Semaphore(10)` combined with 25ms smoothing intervals.
* **Python**: Non-blocking `asyncio.Semaphore(10)` combined with `asyncio.sleep(0.025)` inside `httpx.AsyncClient` throttles outbound coroutines without freezing the single-threaded event loop.

### 3. Open-World vs. Closed-World Completionist Tracking
A common bug in lazy-cached architectures is calculating completion percentages via `COUNT(movies.id)` over local tables:
$$\text{Percentage} = \frac{\text{Watched Movies}}{\text{Locally Cached Movies}} \times 100 \implies 100\% \quad \text{(False Positive)}$$
* **The Solution**: On first director discovery, the system fetches their canonical feature film count directly from TMDB's `/person/{id}/movie_credits` endpoint and stores it as an immutable attribute (`total_directed`) on the `Director` entity.
* Analytical queries run with:
  $$\text{Completion \%} = \frac{\text{Watched Count}}{\max(\text{total\_directed}, \text{Watched Count})} \times 100$$
  This prevents completion gauges from exceeding $100\%$ if TMDB credit records diverge.

### 4. Idempotency & Batch Deduplication
Letterboxd archives contain both temporal event logs (`diary.csv`) and cumulative history (`watched.csv`), often containing duplicates, rewatches, or unrated entries:
* **Null Ratings vs. SQL Constraints**: The database enforces `CHECK (rating >= 0.5 AND rating <= 5.0)`. Unrated films are coerced to `null`/`None` rather than `0.0`. In SQL, `CHECK` conditions evaluate to `UNKNOWN` on `NULL`, successfully passing validation.
* **Compound Keys**: Diary entries deduplicate on `${title}_${year}_${watchedDate}` to preserve legitimate rewatches across different dates while filtering out identical same-day collisions.
* **Database Upserts**:
  * Java: Deduplicated in memory via `ConcurrentHashMap.computeIfAbsent` and checked against DB existence before persisting.
  * Python: Uses PostgreSQL native upserts (`INSERT ... ON CONFLICT DO NOTHING`) via SQLAlchemy's `pg_insert`.

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

## Monorepo Directory Structure

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

## Database Schema (PostgreSQL 16)

```sql
-- 1. Tenants & Session Identities
CREATE TABLE users (
   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   letterboxd_username VARCHAR(100) NOT NULL,
   session_token VARCHAR(255) UNIQUE,
   is_guest BOOLEAN NOT NULL DEFAULT TRUE,
   created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
   last_active_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Master Movie Catalog (Shared Global Dimension)
CREATE TABLE movies (
   id BIGSERIAL PRIMARY KEY,
   tmdb_id INTEGER UNIQUE,
   title VARCHAR(255) NOT NULL,
   release_year SMALLINT NOT NULL,
   runtime_minutes SMALLINT DEFAULT 0,
   poster_path VARCHAR(255),
   backdrop_path VARCHAR(255),
   country_code VARCHAR(10),
   overview TEXT,
   created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
   CONSTRAINT uq_movie_title_year UNIQUE (title, release_year)
);

-- 3. Normalized Directors with Canon Tracking
CREATE TABLE directors (
   id BIGSERIAL PRIMARY KEY,
   tmdb_person_id INTEGER NOT NULL UNIQUE,
   name VARCHAR(150) NOT NULL,
   profile_path VARCHAR(255),
   total_directed INT DEFAULT 0
);

-- 4. User Watch History (Event Fact Table)
CREATE TABLE watch_logs (
   id BIGSERIAL PRIMARY KEY,
   user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
   movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE RESTRICT,
   watched_date DATE,
   rating NUMERIC(2, 1) CHECK (rating >= 0.5 AND rating <= 5.0),
   is_rewatch BOOLEAN NOT NULL DEFAULT FALSE,
   letterboxd_uri VARCHAR(512),
   created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
   CONSTRAINT uq_user_movie_watch UNIQUE (user_id, movie_id, watched_date)
);

-- Analytical B-Tree Indexes
CREATE INDEX idx_watch_logs_user_date ON watch_logs (user_id, watched_date DESC);
CREATE INDEX idx_watch_logs_user_rating ON watch_logs (user_id, rating);
CREATE INDEX idx_movies_lookup ON movies (title, release_year);
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

---

## Technical Interview Questions Mastered

### Q1: Virtual Threads vs. Downstream Rate Limits (The Thundering Herd)
> *"Virtual threads make thread creation practically free in Java 21. Why can't we spawn 1,000 virtual threads to query a third-party API concurrently?"*

**Answer**: Virtual threads eliminate internal memory and thread scheduling bottlenecks on your JVM, but they do nothing to protect downstream dependencies from being overwhelmed. Spawning unbounded tasks against a third-party API (like TMDB) triggers HTTP 429 (Too Many Requests) or TCP resets. High-concurrency architectures must throttle external outbound I/O using concurrency limiters like Java's `Semaphore` or token-bucket rate limiters (`Resilience4j`).

---

### Q2: Fact Tables vs. Dimension Tables Grain
> *"Why did our database show 901 movie records while our dashboard KPI card showed 906 films watched?"*

**Answer**: This represents a grain mismatch between **Dimension** and **Fact** tables.
* `movies` is a shared **Dimension table** holding unique physical entities (cardinality: 901 unique titles).
* `watch_logs` is an **Event Fact table** representing historical actions (cardinality: 906 viewing events).
The difference reflects legitimate rewatches (the user watched 5 films more than once on different dates). Displaying `COUNT(watch_logs.id)` correctly tracks total viewing events, whereas `COUNT(DISTINCT movie_id)` tracks unique titles seen.

---

### Q3: Asynchronous Lazy Loading vs. Hibernate Proxies
> *"Why does accessing relationships in SQLAlchemy AsyncIO require explicit loading strategies like `selectin`, while Spring Data JPA handles lazy loading seamlessly?"*

**Answer**: 
* **Spring Boot (Hibernate)**: Dynamic CGLIB/Bytebuddy proxies intercept synchronous getters (`movie.getGenres()`), borrowing an active JDBC connection from the thread context to run the query synchronously.
* **SQLAlchemy AsyncIO**: Property access (`movie.genres`) is synchronous syntax in Python and cannot contain an `await` expression. An async database driver cannot block an OS thread to perform synchronous socket I/O without freezing the event loop. Therefore, accessing an unloaded relationship raises `MissingGreenlet`. We configure `lazy="selectin"` to eagerly batch-load child collections in an asynchronous secondary `SELECT ... WHERE movie_id IN (...)` query during the primary transaction.

---

### Q4: Query Pushdown vs. In-Memory Aggregation
> *"Why compute overview statistics and director completion percentages inside native SQL queries instead of streaming all rows into Java Streams or Python dictionaries?"*

**Answer**: **Query Pushdown**. Pushing computations down to the PostgreSQL engine leverages index scans (`idx_watch_logs_user_date`) and optimized internal sorting algorithms (e.g., Top-N heap sort). Pulling thousands of unindexed fact rows over the network socket consumes bandwidth, bloats heap memory, and increases garbage collection overhead. Running aggregations directly on the database engine allows the query to return only the final scalar result set.

---

### Q5: Check-Then-Act Race Conditions
> *"Why does `findByX().orElseGet(() -> save(...))` consistently trigger duplicate key errors (SQLState 23505) under high concurrency?"*

**Answer**: `findBy` (check) and `save` (act) execute as two discrete database operations. In high-concurrency environments (multiple virtual threads or coroutines), Thread B can check between Thread A's lookup and commit, finding nothing and issuing a duplicate `INSERT`.
* **Resolution**: Pushing uniqueness enforcement down to the database using atomic upsert semantics:
  * PostgreSQL: `INSERT ... ON CONFLICT (unique_column) DO NOTHING` (via SQLAlchemy `pg_insert`).
  * JVM: Thread-safe atomic maps via `ConcurrentHashMap.computeIfAbsent`.