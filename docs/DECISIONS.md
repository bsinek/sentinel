# Sentinel — Key Decisions

## FastAPI over Django (for now)

**Decision**: Use FastAPI for the API layer instead of Django + DRF.

**Why**: The current scope is compute-heavy request/response — no ORM, no admin, no auth, no complex model relationships. FastAPI with Pydantic gives fast iteration on schemas and endpoints without Django's overhead.

**Trade-off**: Django was originally planned for orchestration and experiment management. When persistence, experiment tracking, and user management become real requirements, Django may be reconsidered. For now, FastAPI fits the stateless compute model.

## yfinance for Market Data

**Decision**: Use yfinance for price data ingestion.

**Why**: Free, no API key required, good enough for research. Gets daily OHLC for any ticker.

**Trade-off**: Rate-limited, unreliable for production, no options chain or intraday data. Will need a real data provider (Polygon, IBKR, etc.) as domains expand.

## Redis for Price Caching (Not Compute Caching)

**Decision**: Cache yfinance price fetches in Redis with 1-day TTL.

**Why**: yfinance calls are slow and rate-limited. Same tickers get requested repeatedly during research. Redis avoids redundant API calls.

**What it's not**: This is not node-level DAG caching. That's a separate system to be designed later.

## Hand-Written SVG Charts (No Charting Library)

**Decision**: PathChart renders sample paths and confidence bands as raw SVG.

**Why**: Avoids heavyweight charting dependencies. The visualization needs are narrow — portfolio path lines and bands. Custom SVG gives full control over rendering with zero dependencies.

**Trade-off**: Won't scale to complex interactive charts. When more chart types are needed, a lightweight library (e.g., D3, Recharts) may be appropriate.

## Linear Pipeline Before DAG

**Decision**: Build the first working domain (Monte Carlo) as a linear pipeline (`runtime/simulate.py`), not as a DAG.

**Why**: The DAG engine is the long-term architecture, but building it before having multiple domains to exercise it would be premature abstraction. The linear pipeline validates the compute modules and API contract. The DAG refactor comes when the second or third domain makes the linear approach break down.

**Status**: The existing `engine/` modules are already structured as independent functions with typed inputs/outputs — they're effectively proto-nodes ready for DAG integration.

## Stateless API (No Persistence Yet)

**Decision**: Simulations are computed on-demand and returned as JSON. Nothing is persisted.

**Why**: Experiment tracking, comparison, and result storage are important but not needed for the MVP. Adding a database before the data model is understood would mean migrations and schema churn.

**When to revisit**: When the user wants to save, compare, or reproduce experiments.

## Pickle Serialization for Redis

**Decision**: Cache price DataFrames using pickle serialization.

**Why**: Simple, handles Pandas DataFrames natively.

**Trade-off**: Not portable across Python versions, not human-readable. Acceptable for a local cache with 1-day TTL. Would reconsider for any shared or long-lived cache.

## No Docker Yet

**Decision**: No containerization.

**Why**: Single-developer local research environment. Docker adds complexity without benefit until there's a deployment target or multi-service orchestration need.

**When to revisit**: When Celery workers, Postgres, and Redis all need to run together reliably.
