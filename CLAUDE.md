# Sentinel — Claude Code Guidelines

## What is Sentinel

Sentinel is a DAG-based quantitative research platform for building and testing flexible research workflows across derivatives, ML, stat arb, order flow, simulation, and realistic backtesting. See [docs/PROJECT.md](docs/PROJECT.md) for full vision and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical design.

## Current State

- **Working MVP**: Monte Carlo GBM simulation end-to-end (frontend → FastAPI → engine → results)
- **Backend**: FastAPI + Redis cache + modular Python engine (`backend/engine/`, `backend/runtime/`)
- **Frontend**: Next.js 16 + React 19 + Tailwind v4, one working page (`/monte-carlo`)
- **Not yet built**: DAG execution engine, persistence layer, Celery workers, multiple quant domains
- See [docs/ROADMAP.md](docs/ROADMAP.md) for what's done and what's next

## Engineering Principles

- Modular system design — computation as independent, composable units
- Separation of compute and orchestration
- Research-first infrastructure — reproducibility over speed
- Incremental complexity — avoid premature abstraction
- Core quantitative modeling is user-driven; Claude assists infrastructure and scaffolding
- Do not implement advanced quant methods without explicit direction

## Git Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages.

Format: `<type>(<scope>): <description>`

Common types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `perf`

Examples:
- `feat(engine): add GBM simulation module`
- `fix(cache): handle Redis connection timeout`
- `docs(claude): add subagent usage rule`
- `refactor(runtime): extract orchestration logic to runtime layer`

## Backend Conventions

- Engine modules in `backend/engine/` are pure computation — no I/O, no side effects
- Orchestration logic lives in `backend/runtime/`
- API layer (`backend/api/`) handles validation and response formatting only
- Redis is used for caching price data (TTL 1 day, pickle serialization)
- Type hints on all public functions

## Frontend Constraints

**Color system:**
- Cohesive theme via CSS variables in `globals.css`
- No ad-hoc colors or inconsistent palettes

**Structure:**
- Single-file pages acceptable when appropriate
- Extract reusable or complex parts into components
- Organize by clarity, not premature abstraction
- Keep component structure shallow and readable

**Complexity:**
- Minimal and focused UI
- No unnecessary dependencies or frameworks
- Prefer simple React + Next patterns
- Build complexity incrementally

**Design quality:**
- No generic, template-style, or AI-generated-looking interfaces
- No standard SaaS dashboard aesthetics
- Cohesive, intentional interface suited to a research environment

## Claude Behavior Rules

**Do not act before instructions:**
Do not jump into implementation or change files unless clearly instructed. When intent is ambiguous, default to research and recommendations. Only proceed with edits when explicitly requested.

**Investigate before answering:**
Never speculate about code you haven't read. Read relevant files before answering questions about the codebase.

**Parallel tool calls:**
Make independent tool calls in parallel. Only sequence calls that have data dependencies.

**Subagent usage for parallelizable work:**
For large tasks that can be parallelized — such as auditing multiple modules, reading multiple files for research, or running independent analyses — spawn parallel subagents rather than working sequentially. Each subagent should have a clearly scoped task (e.g., "audit backend/engine/risk.py for correctness" or "research how Redis caching is used across the runtime layer") and return structured output back to the orchestrator. Prefer subagents when the work involves 3+ independent units that don't depend on each other's results.

**After completing tool-use tasks:**
Provide a brief summary of work completed.
