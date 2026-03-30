# Sentinel

A DAG-based quantitative research platform for building and testing flexible research workflows across derivatives, ML, stat arb, order flow, simulation, and realistic backtesting.

## What is Sentinel

Sentinel is a graph-based quant research and strategy engineering platform. Instead of separate tools for each quant domain, it provides a unified architecture where all research workflows are composed from reusable computational nodes, executed through DAG orchestration, and evaluated under realistic trading assumptions.

It is a research system, not a trading product or dashboard.

## Current State

Working MVP: Monte Carlo GBM simulation running end-to-end — portfolio construction UI, FastAPI backend, modular compute engine, SVG visualization with confidence bands and risk metrics.

The DAG execution engine is the target architecture but not yet implemented. The existing engine modules are structured as independent functions with typed inputs/outputs, ready for DAG integration.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic |
| Frontend | Next.js 16, React 19, Tailwind v4 |
| Compute | NumPy, Pandas, custom Python modules |
| Caching | Redis |
| Data | yfinance |

## Project Structure

```
sentinel/
├── backend/
│   ├── api/          # FastAPI server + Pydantic schemas
│   ├── engine/       # Pure computation modules (data, estimation, GBM, portfolio, projection, risk)
│   ├── runtime/      # Orchestration layer (simulation runner, Redis cache)
│   ├── tasks/        # Celery tasks (placeholder)
│   └── worker/       # Celery worker config (placeholder)
├── web/              # Next.js frontend
│   └── app/
│       ├── monte-carlo/   # Monte Carlo simulation page + PathChart
│       └── ...
├── research/         # Jupyter notebooks
├── docs/             # Project documentation
│   ├── PROJECT.md    # Vision, research domains, north star
│   ├── ARCHITECTURE.md  # Stack, layers, DAG design
│   ├── DECISIONS.md  # Key choices and trade-offs
│   └── ROADMAP.md    # What's done, what's next
├── CLAUDE.md         # Claude Code guidelines
└── README.md
```

## Running Locally

```bash
# Backend
cd backend
source ../venv/bin/activate
uvicorn api.main:app --reload

# Frontend
cd web
npm run dev

# Redis (required for caching)
redis-server
```

## Documentation

- [Project Vision](docs/PROJECT.md) — what Sentinel is and where it's going
- [Architecture](docs/ARCHITECTURE.md) — stack, system layers, DAG design
- [Decisions](docs/DECISIONS.md) — key technical choices and trade-offs
- [Roadmap](docs/ROADMAP.md) — what's built, what's next
