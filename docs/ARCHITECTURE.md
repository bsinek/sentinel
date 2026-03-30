# Sentinel — Architecture

## System Layers

```
┌─────────────────────────────────────────────┐
│  Interface Layer                             │
│  (API endpoints, frontend, CLI)              │
├─────────────────────────────────────────────┤
│  Graph Definition Layer                      │
│  (nodes, schemas, graph construction)        │
├─────────────────────────────────────────────┤
│  Execution / Orchestration Layer             │
│  (DAG scheduling, dependency resolution,     │
│   task dispatch, caching)                    │
├─────────────────────────────────────────────┤
│  Compute Layer                               │
│  (quant/stat/ML functions, engine modules)   │
├─────────────────────────────────────────────┤
│  Storage / Caching Layer                     │
│  (datasets, intermediate artifacts, results, │
│   metadata, Redis cache)                     │
└─────────────────────────────────────────────┘
```

## Current Stack

| Layer | Technology | Status |
|---|---|---|
| **API** | FastAPI + Pydantic | Implemented |
| **Frontend** | Next.js 16, React 19, Tailwind v4 | Implemented (one page) |
| **Compute** | NumPy, Pandas, custom Python modules | Implemented (GBM domain) |
| **Caching** | Redis (price data, TTL 1 day) | Implemented |
| **Orchestration** | `runtime/simulate.py` (linear pipeline) | Implemented (pre-DAG) |
| **DAG Engine** | — | Not started |
| **Persistence** | — | Not started |
| **Async Workers** | Celery (in requirements, not wired) | Not started |
| **Database** | PostgreSQL (planned) | Not started |

## Current Architecture Flow

```
Web (Next.js)
    ↓  POST /simulate
FastAPI (api/main.py)
    ↓
Runtime (runtime/simulate.py)
    ├→ Redis cache check
    ├→ yfinance data fetch
    ├→ Parameter estimation
    ├→ GBM simulation
    ├→ Portfolio aggregation
    └→ Risk metrics + Projection
    ↓
JSON Response → PathChart + Metrics
```

## Backend Structure

```
backend/
├── api/
│   ├── main.py          # FastAPI server, /health and /simulate endpoints
│   └── schemas.py       # Pydantic request/response models
├── engine/              # Pure computation modules (no I/O)
│   ├── data.py          # Market data fetching (yfinance)
│   ├── estimation.py    # Parameter estimation (mu, cov)
│   ├── gbm.py           # Geometric Brownian Motion simulation
│   ├── portfolio.py     # Portfolio aggregation
│   ├── projection.py    # Confidence bands, sample paths
│   └── risk.py          # Risk metrics (VaR, CVaR, Sharpe, drawdowns, etc.)
├── runtime/             # Orchestration layer
│   ├── simulate.py      # Main simulation runner
│   └── cache.py         # Redis caching logic
├── tasks/               # Celery tasks (placeholder)
└── worker/              # Celery worker config (placeholder)
```

## Frontend Structure

```
web/app/
├── page.tsx                    # Home page
├── layout.tsx                  # Root layout
├── globals.css                 # Tailwind theme + CSS variables
└── monte-carlo/
    ├── page.tsx                # Monte Carlo simulation UI
    └── PathChart.tsx           # SVG path visualization
```

## Target DAG Architecture

The planned evolution replaces the linear pipeline with a graph execution engine:

### Node Model

Each node:
- Takes typed inputs
- Performs a defined computation
- Returns typed outputs
- Can be cached at its boundary
- Can be reused across graphs

### Node Categories (Planned)

| Category | Examples |
|---|---|
| Data ingestion | Price fetch, options chain, order flow |
| Transformation | Returns calculation, normalization, resampling |
| Feature engineering | Technical indicators, derived features |
| Statistical modeling | Cointegration, parameter estimation |
| Simulation | GBM, jump-diffusion, scenario generation |
| Pricing / Derivatives | IV extraction, surface fitting, greeks |
| ML Training | Model fit, hyperparameter search |
| Inference | Model predict, ensemble |
| Signal generation | Z-scores, crossover, regime detection |
| Portfolio construction | Optimization, weight allocation |
| Backtest | Strategy execution, order simulation |
| Execution / Slippage | Fill modeling, cost estimation |
| Evaluation / Risk | VaR, Sharpe, drawdown, attribution |

### DAG Benefits

- **Modularity**: Reuse nodes across different research pipelines
- **Extensibility**: New quant domain = define new nodes, not rewrite the system
- **Selective recomputation**: Only re-run nodes whose inputs changed
- **Node-level caching**: Cleaner than ad-hoc endpoint caching
- **Composability**: Options research and stat arb are both just DAGs of computations

## API Design

### Current Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/simulate` | Run Monte Carlo simulation |

### CORS

Configured for `http://localhost:3000` (Next.js dev server).
