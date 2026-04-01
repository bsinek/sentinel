# Celery Integration & Backend Restructure

## Context

Sentinel's Monte Carlo simulation currently runs synchronously — the HTTP connection stays open for the entire duration of the computation. This means long simulations risk HTTP timeouts (browsers/proxies cut connections after 30-60s), and the API process can't serve other requests while it's waiting on a simulation. As we prepare to add more pipelines (volatility surfaces, stat arb, etc.), we need to decouple job submission from execution so the API responds immediately and computation happens in a separate worker process. This spec covers adding Celery with Redis as broker, restructuring the backend for multiple pipelines, containerizing with Docker Compose, and updating the frontend to a submit-then-poll pattern.

## Scope

- Restructure backend: `runtime/` splits into `services/` + `pipelines/`
- Celery integration with Redis broker
- New async job API (`POST /jobs`, `GET /jobs/{id}`) replacing sync `POST /simulate`
- Docker Compose for API + worker + Redis
- Frontend update to submit + poll

## Backend Structure (After)

```
backend/
├── celery.py              # Celery app config (Redis broker + result backend)
├── api/
│   ├── main.py            # POST /jobs, GET /jobs/{id}, GET /health
│   └── schemas.py         # + JobSubmitResponse, JobStatusResponse
├── engine/                # unchanged (pure computation)
├── pipelines/
│   └── simulate.py        # moved from runtime/simulate.py
├── services/
│   └── cache.py           # moved from runtime/cache.py, env var for Redis URL
└── tasks/
    └── simulate.py        # Celery task wrapping pipelines/simulate.py
```

## Redis Database Layout

- DB 0: Celery broker (task queue)
- DB 1: Celery result backend (task state + results)
- DB 2: price cache (`services/cache.py`)

## Celery Configuration

- Broker: Redis DB 0 (`REDIS_URL` env var, defaults to `redis://localhost:6379`)
- Result backend: Redis DB 1 — single source of truth for job state
- JSON serialization for tasks
- `task_track_started=True` to distinguish pending vs running
- `task_acks_late=True` to prevent task loss on worker crash
- `worker_prefetch_multiplier=1` (one task at a time per worker process)
- `worker_concurrency=2` (max 2 simultaneous simulations; leaves CPU cores free for local dev)
- `worker_max_tasks_per_child=50` (restart worker process after 50 tasks; prevents numpy/pandas memory accumulation)
- No TTL on results — app is ephemeral by design; results only need to outlive the current browser session

## Job Lifecycle

```
POST /jobs (SimulationRequest)
  → enqueue Celery task
  → return { job_id } immediately

Worker picks up task:
  → Celery automatically marks task as STARTED
  → run_simulation() executes
  → Celery automatically stores result and marks SUCCESS
  → on exception: Celery stores error and marks FAILURE

GET /jobs/{id}
  → query AsyncResult(job_id) from Celery result backend
  → map Celery states to API states
  → return { job_id, status, result?, error? }
```

**Celery → API state mapping:**
- `PENDING` → `pending`
- `STARTED` → `running`
- `SUCCESS` → `completed`
- `FAILURE` → `failed`

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

Thin wrapper — Celery handles all state management automatically:
1. Reconstruct `SimulationRequest` from the dict params
2. Call `run_simulation(req)`
3. Return result dict via `model_dump()` — Celery stores it on SUCCESS
4. On exception: Celery records the error and marks FAILURE automatically

No manual state updates needed.

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

`cache.py` updated to read `REDIS_URL` from environment and use DB 2.

## Frontend Changes

The `/monte-carlo` page switches from sync fetch to submit + poll:

1. `POST /jobs` with simulation params → receive `job_id`
2. Poll `GET /jobs/{job_id}` every 1 second
3. When `completed`: extract `result.metrics` and `result.projection`, render as before
4. When `failed`: show error
5. Button text reflects state: "Queued..." → "Simulating..." → done
6. Cleanup polling on component unmount via ref

## Implementation Order

1. **Restructure directories** — move files, update imports ✅
2. **Add Celery infrastructure** — celery.py, tasks/simulate.py, worker/config.py
3. **New API endpoints** — replace /simulate with /jobs and /jobs/{id}
4. **Update cache.py** — env var for Redis URL, switch to DB 2
5. **Docker setup** — Dockerfile + docker-compose.yml
6. **Frontend update** — submit + poll pattern

## Dependencies

Add to `requirements.txt`:
- `celery==5.4.0`
