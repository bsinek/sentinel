# Sentinel — Roadmap

## What's Done

### Monte Carlo Simulation (MVP) ✓

- [x] Engine modules: data fetch, parameter estimation, GBM simulation, portfolio aggregation, projection, risk metrics
- [x] FastAPI endpoint (`POST /simulate`)
- [x] Pydantic request/response schemas
- [x] Redis price caching with TTL
- [x] Next.js frontend with portfolio construction UI
- [x] SVG path chart with confidence bands
- [x] Risk metrics display (VaR, CVaR, Sharpe, drawdowns, prob of loss, etc.)
- [x] Logging (replaced print statements)

## What's Next

Priority is roughly top-to-bottom, but subject to change based on research direction.

### Near-Term: Foundation

- [ ] **Node abstraction** — Define a base node interface (typed inputs/outputs, cacheable, composable). Refactor existing engine modules into this interface.
- [ ] **Graph definition** — Schema for defining DAGs of nodes. Validation that graphs are acyclic and type-compatible.
- [ ] **DAG executor** — Dependency-aware execution of node graphs. Start simple (synchronous, single-thread), add async later.
- [ ] **Node-level caching** — Cache intermediate results at node boundaries, keyed by input hash.

### Medium-Term: Second Domain

- [ ] **Options / Derivatives** — Options chain ingestion, IV extraction, volatility surface fitting, greeks
- [ ] **Statistical Arbitrage** — Spread generation, cointegration testing, mean reversion signals, z-scores
- [ ] Pick whichever domain is most interesting or useful as the second workflow to validate the DAG architecture.

### Medium-Term: Infrastructure

- [ ] **Persistence** — PostgreSQL for experiment configs, results, metadata. Define the data model once there are at least 2 workflow types to inform it.
- [ ] **Async execution** — Celery workers for long-running graph executions. Redis as broker.
- [ ] **Experiment tracking** — Save, compare, and reproduce workflow runs.

### Longer-Term: Platform Expansion

- [ ] **ML pipelines** — Feature engineering, model training/inference, walk-forward validation as graph workflows
- [ ] **Order flow / microstructure** — Trade-level data, imbalance metrics, short-horizon alpha
- [ ] **Realistic execution modeling** — Slippage, fees, market impact, fill simulation, position constraints
- [ ] **Frontend workflow builder** — Visual graph construction / inspection
- [ ] **Docker / deployment** — Containerize when multi-service orchestration is needed

## Guiding Principle

Build the next thing that's needed, not the thing that's architecturally elegant in theory. The DAG engine earns its complexity when the second domain makes the linear pipeline break down.
