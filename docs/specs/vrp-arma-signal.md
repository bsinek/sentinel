# VRP-ARMA Signal -- Research Spec

## Overview

Build a forward-looking variance risk premium (VRP) signal using a two-model pipeline:

1. **GARCH(1,1)** -- estimates daily conditional vol from SPY log returns. Used as a clean realized vol proxy, avoiding the mechanical autocorrelation introduced by a rolling window.
2. **ARMA(p,q)** -- models the persistence structure of VRP. Generates 1-step-ahead forecasts of tomorrow's VRP, which serve as the entry/exit signal.

**Core question:** Does current VRP predict future VRP? If VRP is autocorrelated (which vol clustering implies it should be), an ARMA model can forecast when elevated VRP will persist vs revert -- giving a principled forward-looking entry signal rather than just reacting to today's level.

**Notebook:** `research/vrp_arma_signal.ipynb`

---

## Research Background

### Why VRP is likely autocorrelated

Vol clustering is well-established (Engle 1982, Bollerslev 1986) -- large moves tend to cluster in time. This means:
- Realized vol today predicts realized vol tomorrow
- VIX is sticky and mean-reverting (not i.i.d.)
- Therefore VRP = VIX - realized_vol is also persistent

If the hypothesis holds, ACF/PACF of VRP should show significant autocorrelation, and ADF should confirm stationarity.

### Why GARCH over rolling vol for VRP construction

A 21-day rolling window creates mechanical autocorrelation at lags 1-21 by construction -- 20 of the 21 days overlap with the next day's window. This inflates the apparent ACF of VRP and would distort ARMA order selection. GARCH conditional vol updates daily without window overlap, giving a cleaner input series.

### Why ARMA is appropriate

VRP = VIX - GARCH_vol. Both VIX and GARCH vol are mean-reverting, so their difference is likely stationary -- the core ARMA requirement. Stationarity should be verified with ADF before fitting.

---

## Data

```python
df = yf.download(['SPY', '^VIX'], start='2016-01-01', end='2026-01-01', interval='1d', auto_adjust=True)['Close']
```

Train: 2016-2022. Test (OOS): 2022-2026. `TRAIN_END = '2022-01-01'`. The 2022 cutoff is a natural structural break -- the Fed rate hike cycle began and the vol regime shifted, making it a meaningfully harder OOS period.

---

## Pipeline

### Step 1 -- GARCH(1,1) conditional vol

Fit GARCH(1,1) on train period. Compare Student-t vs normal innovations by AIC/BIC -- SPY returns have fat tails, so Student-t is expected to win. Carry parameters forward into OOS without refitting. Verify residuals are white noise (Ljung-Box).

### Step 2 -- VRP construction

```python
vrp = vix_decimal - garch_cond_vol   # vol space, annualized decimal
```

Compute descriptive stats on the full series: unconditional fraction of days with VRP > 0, mean VRP, CVaR at the 95th percentile for an always-in position.

### Step 3 -- Stationarity + ACF/PACF

- Run ADF on train VRP -- stationarity is required for ARMA
- Plot ACF and PACF to identify likely p, q order
- Expected: AR-dominated structure (PACF drops sharply, ACF decays geometrically)

### Step 4 -- ARMA(p,q) fit

Grid search over p,q ∈ {0..3} (excluding p=q=0) on train VRP, selecting by AIC. Verify Ljung-Box on residuals -- model should capture the autocorrelation structure and leave white noise.

### Step 5 -- OOS 1-step-ahead forecasts

Walk-forward: at each OOS day t, forecast VRP at t+1 using all data up to t. ARMA parameters fixed at train values -- no refitting on OOS data. Evaluate RMSE and MAE against naive persistence (today's VRP as tomorrow's forecast).

### Step 6 -- Trading rule + backtest

Compare three strategies over OOS:
- **Always-in**: long vol spread every day
- **Naive binary**: in when today's VRP > 0
- **ARMA-timed**: in when ARMA forecast of tomorrow's VRP > 0

Evaluate each on days in, hit rate, mean VRP captured, std VRP, and CVaR (loss tail). The key question is whether ARMA's lead-time at zero-crossings improves sign accuracy over naive persistence.

---

## Known Gotchas

- **Mechanical ACF inflation** -- rolling_vol would inflate ACF lags 1-21. GARCH-based VRP avoids this.
- **Look-ahead bias** -- walk-forward forecasting uses only data available at time t. No refitting on OOS data.
- **OOS regime shift** -- if the OOS period represents a structural break from train, ARMA parameters may not generalize. Naive persistence is a natural baseline to benchmark against.
- **Sharpe invalidity** -- VRP is a vol spread, not a return. mean/std × √252 is not a Sharpe ratio; std should be reported separately.

---

## Explicit Non-Goals

- No intraday data or high-frequency realized vol.
- No options pricing, vol surface, or variance swap construction.
- No rolling GARCH re-estimation (fit once on train, carry forward).
- No HMM integration in this notebook (potential future combination).
- No new engine modules or backend integration. Research notebook only.
