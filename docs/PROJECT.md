# Sentinel — Project Vision

## One-line Summary

Sentinel is a DAG-based quant research platform for building and testing flexible research workflows across derivatives, ML, stat arb, order flow, simulation, and realistic backtesting.

## What Sentinel Is

Sentinel is a **graph-based quantitative research and strategy engineering platform**. It is a research system, not a trading product or dashboard.

Instead of building separate tools for each quant domain, Sentinel provides a common architecture where all research workflows live inside one unified framework. The core question is not "how do we add options?" or "how do we add stat arb?" — it's "how do we build a system where options, stat arb, ML, order flow, and backtesting are all just different graph-defined workflows?"

## Core Idea: DAG / Node Architecture

The fundamental technical structure is a **DAG (directed acyclic graph) execution engine** where:

- **Nodes** = units of computation / transformation / analysis
- **Edges** = dependencies / data flow
- **Graphs** = full research pipelines
- **DAG execution** = deterministic execution order for dependent tasks

This matters because once you want to support options surfaces, ML feature pipelines, stat arb spread construction, cointegration testing, order flow aggregation, and slippage-aware backtests — a fixed linear pipeline becomes too limiting. A DAG structure makes workflows composable.

### Example Workflows as Graphs

- Options chain → IV extraction → surface fitting → signal generation
- Raw data → features → ML model → predictions → signals → execution simulation → metrics
- Pair selection → cointegration testing → spread model → backtest → cost-adjusted performance
- Order flow data → imbalance features → short-horizon alpha model → realistic fill simulation

## Research Domains

Sentinel is designed to support multiple major quant domains:

| Domain | Scope |
|---|---|
| **Derivatives / Options** | Chains, implied vol, surfaces, smile/skew, term structure, greeks |
| **ML Price Prediction** | Feature engineering, training, inference, walk-forward validation |
| **Statistical Arbitrage** | Spread generation, cointegration, mean reversion, z-scores |
| **Order Flow / Microstructure** | Trade/book data, imbalance metrics, signed volume, short-horizon alpha |
| **Portfolio Modeling** | Construction, optimization, Monte Carlo simulation |
| **Realistic Backtesting** | Slippage, fees, execution assumptions, market impact, position constraints |

## Realistic Simulation as a Core Pillar

Sentinel is not just a signal lab. It is a **strategy validation environment**. Research must be evaluated under realistic conditions:

- Slippage and spread costs
- Transaction fees
- Execution-aware results
- Market impact approximations
- Position constraints

The question is not just "did the signal work in theory?" but "did it survive realistic trading assumptions?"

## What Sentinel Is Not

- Not a trading system or execution platform
- Not a dashboard or analytics app
- Not a single-model simulator
- Not a narrow portfolio optimizer

## North Star

A quant operating environment where diverse research workflows are built from reusable nodes, executed through DAG orchestration, and evaluated under realistic trading assumptions.
