# Celery Integration & Backend Restructure

## Context

Sentinel's Monte Carlo simulation currently runs synchronously — the HTTP connection stays open for the entire duration of the computation. This means long simulations risk HTTP timeouts (browsers/proxies cut connections after 30-60s), and the API process can't serve other requests while it's waiting on a simulation. As we prepare to add more pipelines (volatility surfaces, stat arb, etc.), we need to decouple job submission from execution so the API responds immediately and computation happens in a separate worker process. This spec covers adding Celery with Redis as broker, restructuring the backend for multiple pipelines, containerizing with Docker Compose, and updating the frontend to a submit-then-poll pattern.

## Scope

- Restructure backend: `runtime/` splits into `services/` + `pipelines/`
- Celery integration with Redis broker
- New async job API (`POST /jobs`, `GET /jobs/{id}`) replacing sync `POST /simulate`
- Job state management in Redis
- Docker Compose for API + worker + Redis
- Frontend update to submit + poll

## Backend Structure (After)

```
backend/
├── celery.py              # Celery app config (Redis broker)
├── api/
│   ├── main.py            # POST /jobs, GET /jobs/{id}, GET /health
│   └── schemas.py         # + JobSubmitResponse, JobStatusResponse
├── engine/                # unchanged (pure computation)
├── pipelines/
│   └── simulate.py        # moved from runtime/simulate.py
├── services/
│   ├── cache.py           # moved from runtime/cache.py, env var for Redis URL
│   └── jobs.py            # job state management in Redis
├── tasks/
│   └── simulate.py        # Celery task wrapping pipelines/simulate.py
└── worker/
    └── config.py          # Worker tuning params
```

## Celery Configuration

- Broker: Redis DB 0 (`REDIS_URL` env var, defaults to `redis://localhost:6379`)
- Result backend: Redis DB 1
- JSON serialization for tasks
- `task_track_started=True` to distinguish pending vs running
- `task_acks_late=True` to prevent task loss on worker crash
- `worker_prefetch_multiplier=1` (one task at a time per process)
- `result_expires=3600` (1 hour)

## Job Lifecycle

```
POST /jobs (SimulationRequest)
  → enqueue Celery task
  → create job record in Redis (status: pending)
  → return { job_id }

Worker picks up task:
  → update job status to "running"
  → call run_simulation() from pipelines/simulate.py
  → on success: store result, update status to "completed"
  → on failure: store error message, update status to "failed"

GET /jobs/{id}
  → return { job_id, status, result?, error? }
```

**Job states:** `pending` → `running` → `completed` | `failed`

## Job State Management (`services/jobs.py`)

- Redis keys prefixed with `job:` (separate from `prices:` cache keys and Celery internal keys)
- Jobs stored as JSON strings with 1-hour TTL
- Three functions: `create_job()`, `update_job()`, `get_job()`
- Uses `decode_responses=True` (JSON mode), separate client from the pickle-based cache

## API Endpoints

### `POST /jobs`

Request body: same `SimulationRequest` as the old `/simulate` endpoint.

Response:
```json
{ "job_id": "uuid-string" }
```

### `GET /jobs/{job_id}`

Response:
```json
{
  "job_id": "uuid-string",
  "status": "pending" | "running" | "completed" | "failed",
  "result": { "metrics": {...}, "projection": {...} } | null,
  "error": "error message" | null
}

```

The `result` field reuses the existing `SimulationResponse` schema. Populated only when status is `completed`.

### `GET /health`

Unchanged.

## Celery Task (`tasks/simulate.py`)

Thin wrapper:
1. Updates job status to `running`
2. Reconstructs `SimulationRequest` from the dict params
3. Calls `run_simulation(req)` (same function as today, just moved to `pipelines/`)
4. Converts result to dict via `model_dump()`
5. Stores result and updates job to `completed`
6. On exception: stores error string, updates to `failed`, re-raises

Uses `bind=True` to access `self.request.id` as the job ID (Celery's auto-generated UUID).

## Docker Compose

Single `Dockerfile` (Python 3.12-slim), three services:

| Service | Command | Port |
|---------|---------|------|
| redis | redis:7-alpine | 6379 |
| api | `uvicorn backend.api.main:app` | 8000 |
| worker | `celery -A backend.celery worker` | — |

- `REDIS_URL=redis://redis:6379` passed to api and worker
- Redis health check gates api and worker startup
- `redis_data` volume for persistence
- Frontend not containerized (runs via `npm run dev`)

`cache.py` updated to read `REDIS_URL` from environment (replaces hardcoded localhost).

## Frontend Changes

The `/monte-carlo` page switches from sync fetch to submit + poll:

1. `POST /jobs` with simulation params → receive `job_id`
2. Poll `GET /jobs/{job_id}` every 1 second
3. When `completed`: extract `result.metrics` and `result.projection`, render as before
4. When `failed`: show error
5. Button text reflects state: "Queued..." → "Simulating..." → done
6. Cleanup polling on component unmount via ref

## Implementation Order

1. **Restructure directories** — move files, update imports, verify existing functionality works
2. **Add Celery infrastructure** — celery.py, services/jobs.py, tasks/simulate.py, worker/config.py
3. **New API endpoints** — replace /simulate with /jobs and /jobs/{id}
4. **Update cache.py** — env var for Redis URL
5. **Docker setup** — Dockerfile + docker-compose.yml
6. **Frontend update** — submit + poll pattern

## Dependencies

Add to `requirements.txt`:
- `celery==5.4.0`
