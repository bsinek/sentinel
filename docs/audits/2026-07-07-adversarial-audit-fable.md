# Adversarial Audit — 2026-07-07 (Claude Fable 5)

**Provenance:** Run 2026-07-07 by Claude Fable 5 via three parallel audit subagents (VRP-ARMA, HMM, platform). Scope: methodology (lookahead, costs, calibration, significance, overfitting) + code correctness. Findings marked **[verified by execution]** were numerically confirmed; all others rest on code reading in one session — re-verify before acting on anything surprising. A parallel Opus audit is saved separately in this directory.

**Repo state at audit:** commit `36ad14a` (main), plus untracked `research/generate_report.py`.

**Cell numbers** are 0-indexed positions in the notebooks.

---

## Verdict summary

- **VRP-ARMA:** headline conclusion ("naive persistence beats ARMA OOS") is substantially an artifact of an off-by-one bug (V-C1); the quantity forecast is not the VRP (V-C2) and the "P&L" is not P&L (V-C3). Invalid until fixed and re-run.
- **HMM:** headline result (Sharpe 1.22 vs 0.66, MaxDD −6.4%) rests on smoothed/Viterbi decoding of the full test sequence — anticipative by construction (H-C1). Invalid until re-run with filtered inference.
- **Platform:** engineering skeleton solid (GBM discretization, VaR/CVaR/MDD math verified correct; pinned deps; clean Celery wiring), but multi-asset portfolio math is critically wrong (P-C1) and there is no seed handling anywhere.
- **Cross-cutting pattern:** hygiene is above average, but core numbers were never validated against hand-computed cases, and specs/README assert validity claims ("no data leakage", "no lookahead bias") that the code contradicts.

---

# VRP-ARMA (`research/vrp_arma_signal.ipynb`, `docs/specs/vrp-arma-signal.md`, `research/generate_report.py`)

## CRITICAL

- [ ] **V-C1 — Walk-forward off-by-one: ARMA scored as 2-step forecast vs naive's 1-step.**
  Location: notebook cell 33 (reused in cell 36); duplicated `research/generate_report.py:143-160`.
  Evidence: the loop calls `current.forecast(steps=1)` **before** `current = current.append([vrp_val])`, so `forecasts[i]` = E[VRP_i | data ≤ i−1]; it is then compared to `actuals[i] = oos_vrp[i+1]` while `naive[i] = oos_vrp[i]` uses day-i information exactly.
  Impact: with AR persistence ≈ 0.87, the RMSE gap (0.0399 vs 0.0327), hit-rate gap (87.9% vs 92.3%), and cell 38 conclusions #3–#4 ("ARMA failed in both dimensions") are largely this bug. The report's narrative ("ARMA extrapolated persistence into vol spikes") dresses it up as an economic finding.
  Fix: append the day-t observation before forecasting; re-run RMSE + backtest; rewrite every ARMA-vs-naive conclusion.
  **[verified by execution 2026-07-24]** Re-run from the committed CSV: as-coded reproduces the notebook (ARMA RMSE 0.0399 vs naive 0.0327; corr(fc, VRP_t)=0.78 > corr(fc, VRP_{t+1})=0.65, confirming the forecast targets day t). Corrected alignment: ARMA RMSE **0.0318** vs naive 0.0327 — ARMA modestly ahead, directional accuracy 87.7% vs 87.6% (dead even). Diebold-Mariano (squared error, NW lags): corrected ARMA vs naive DM=−1.04, p=0.30 — **not significant**; the as-coded "naive wins" was significant (p=0.03) only because of the bug. Defensible corrected conclusion: ARMA ≈ naive persistence, statistically indistinguishable OOS — not a naive win, not an ARMA win.

- [ ] **V-C2 — "VRP" is horizon-mismatched: 30-calendar-day VIX minus 1-day-ahead GARCH vol.**
  Location: notebook cell 23 (`df['vrp'] = df['vix_decimal'] - df['garch_cond_vol']`); spec line 56; generate_report.py:120.
  Mechanism: under vol mean reversion, 30-day expected vol > 1-day conditional vol on most days even with zero risk premium — the "82.1% positive, VIX systematically overprices realized vol" result is substantially a term-structure artifact; sign flips at spikes are the 1-day leg overshooting (notebook itself notes this in cell 21). √252 trading-day vs VIX calendar-day annualization compounds the level bias.
  Fix: rebuild the realized leg as GARCH-implied expected average vol over the matched forward 21-trading-day horizon (iterate the recursion); restate all level statistics.

- [ ] **V-C3 — "Cumulative VRP captured" is not P&L of any instrument, and half the payoff is known at decision time.**
  Location: notebook cell 36 (`actual_next[signal].cumsum()`); generate_report.py:156-175, 227-232; report §3–4 and slide.
  Mechanism: (a) summed spread *levels* correspond to no tradeable position (VIX spot untradeable; var swap earns spread changes or implied-minus-future-realized); (b) in VRP_{t+1} = VIX_{t+1} − σ_{t+1}, the GARCH leg σ_{t+1} is deterministic given day-t info, so "predicting the sign" reduces to predicting whether VIX_{t+1} beats a known number — source of the 92.3% hit rate. No costs, roll, margin, or slippage anywhere.
  Fix: restate outputs as forecast-accuracy diagnostics and strip P&L language from report/slide, or backtest an actual instrument (front VIX future / short-dated straddle) with costs.

## HIGH

- [ ] **V-H1 — Report overstates: "no lookahead bias", "the VRP edge is real", "confirming there is no regime bias".**
  Location: report §2, §4 (generate_report.py); notebook cell 10; spec line 89.
  The pipeline is causally safe, but "no lookahead bias" printed next to V-C1 reads as verified correctness; "edge is real" asserts an economic fact from a mismatched non-tradeable spread; cell 10's "no regime bias" is a shading plot, not a test.
  Fix: downgrade each claim to what was verified.

- [ ] **V-H2 — Actionability claims with zero cost/turnover analysis.**
  Location: report §4 (generate_report.py:524-537), slide, notebook cell 38 finding #6 ("straightforward to implement", "candidate for integration ... for live monitoring").
  The binary signal flips exactly at high-vol episodes where vol-instrument liquidity is worst.
  Fix: add turnover count + cost-sensitivity table, or delete actionability claims.

## MEDIUM

- [ ] **V-M1 — "CVaR 95%" is mislabeled and rests on ~3 observations.** generate_report.py:47-48, 165: it is the mean of the worst 5% of *losing* days (not of all days), so it's a different effective quantile per strategy; for naive binary (~62 losing days) it averages ~3 points. The headline "tail loss −0.280 → −0.110" comparison is quantile-inconsistent. Fix: fixed-quantile CVaR on each strategy's full active-day distribution + report obs counts.
- [ ] **V-M2 — No significance testing anywhere.** Cells 33/36/38: "Naive binary dominates on every metric" from ~35–50 disagreement days, autocorrelated payoff, no Diebold-Mariano / McNemar / bootstrap. Fix: add DM test on RMSE, paired test on disagreement days, block-bootstrap CIs.
- [ ] **V-M3 — ARMA(3,3) selection fragile.** Cells 2, 29: in-sample Gaussian AIC on a series with kurtosis 27.4, skew −2.6, Het-H 5.07 (p=0.00); `ConvergenceWarning` globally suppressed during grid search; BIC prefers ARMA(2,0) and is ignored; `ma.L1` p=0.139; no squared-residual test; GARCH α+β = 0.9928 frozen over 4 OOS years with no stability check. Fix: select by BIC/train-validation, check convergence flags, test squared residuals, rolling-refit stability.
- [ ] **V-M4 — Winner selected on the test set.** Cell 38 / report §4: naive binary was a baseline, promoted after OOS comparison of 3 strategies — its OOS metrics carry selection bias with no fresh holdout. Fix: label as post-hoc selected; confirm on extended data before any pipeline use.
- [ ] **V-M5 — Internal one-day misalignment in VRP itself.** Cells 18/20/23: σ_t is determined at t−1, so VIX_t jumps a day before the GARCH leg at shock onsets → mechanical one-day positive VRP spike, then collapse — flatters persistence rules at transitions. Fix: use σ_{t+1} (known at close t) or a filtered same-day estimate as the realized leg.

## LOW

- [ ] **V-L1** — Cell 7: `dropna` discards 21 rows for an unused `rolling_vol` plotting column.
- [ ] **V-L2** — generate_report.py:243: hit-rate y-axis truncated to (0.7, 1.0), visually exaggerating differences.
- [ ] **V-L3** — Report hardcodes "2,515 trading days" (actual: 2,514 / 2,493 post-dropna); "difference is stationary, confirmed statistically" — ADF was train-only.
- [ ] **V-L4** — Cell 21: "Garch is the better proxy" asserted right after admitting it wasn't empirically shown.

---

# HMM (`research/hmm.ipynb`, `docs/specs/hmm-regime-detection.md`)

## CRITICAL

- [ ] **H-C1 — Smoothed/Viterbi state inference over the full test set = lookahead.**
  Location: notebook cell 12 (`test_regimes = model_wf.predict(X_test)`, `proba_wf = model_wf.predict_proba(X_test)`), consumed by backtests in cells 14–16.
  Mechanism: hmmlearn `predict` = Viterbi over the whole passed sequence; `predict_proba` = forward-backward (smoothed) — both condition day t on observations after t. Train-only fitting prevents *parameter* leakage but not *inference* leakage. Smoking gun: cell 14 output shows the strategy going flat on **2022-01-05** — the exact top before the 2022 bear — when drawdown ≈ 0 and vol was low; only a decoder that sees the coming decline labels that day Correction. Headline Sharpe 1.22 vs 0.66 and MaxDD −6.42% vs −24.47% rest on this.
  Fix: filtered decoding — at each t decode only `X_test[:t+1]` (or incremental forward recursion); trade on the last filtered state/posterior; re-run.

  **[fixed + verified by execution 2026-08-05]** Confirmed from `hmmlearn/base.py`: `predict` -> `decode` -> Viterbi (docs: "most likely sequence of states, given all emissions"); `predict_proba` -> `score_samples`, which runs `forward_log` AND `backward_log` and forms posteriors as `fwdlattice + bwdlattice`. Demonstrated directly: with parameters frozen and no refit, the label on 2022-01-05 reads Recovery when decoded from data up to that day and flips to Correction once a single later day enters the window. Full-block vs filtered decoding disagree on 61 of 1003 test days, clustered on regime turns. Notebook now decodes causally (`filtered_posteriors`). Corrected result: Sharpe **0.92** vs 0.66, MaxDD **-10.94%** vs -24.47%, total return 31.10% vs 50.91% (was 1.22 / -6.42% / 43.32%). Direction of the finding is confirmed; magnitude is a haircut, not a collapse. Costs (H-H2/H-H3) and refits (H-M1) remain unaddressed.

## HIGH

- [ ] **H-H1 — Spec and README assert "no data leakage" / "out-of-sample" for a leaked backtest.** Spec line 226; README lines 15, 67. False as written given H-C1. Fix first — these misdirect every future reader.
- [ ] **H-H2 — Zero transaction costs, no turnover measurement.** Cells 14–16: no cost term anywhere; 188 regime runs in ~10y in-sample (Recovery mean 9.3 days); soft variant rebalances daily by construction; strategy's total-return edge is already negative (43.32% vs 50.91%). Fix: compute turnover, apply 2–10 bps per switch to both variants.
- [ ] **H-H3 — Soft-vs-hard comparison confounded; violates the spec's own rule.** Cell 16 sizes with `proba_wf_smooth` (10-day rolling mean) which spec line 193 marks "display-only — do not smooth before feeding to the model or backtest"; hard variant uses unlagged Viterbi labels, so soft loses partly by construction; spec line 183 then elevates the winner to a live recommendation. Both variants inherit H-C1. Fix: rerun both on unsmoothed *filtered* posteriors with costs.
- [ ] **H-H4 — Fabricated parameter provenance + BIC self-contradiction.** Cell 3 / spec lines 105–107 attribute `vol_window=20`, `drawdown_window=60` to Guidolin & Timmermann (2007) — a monthly, raw-excess-returns paper with no rolling-vol/drawdown features or daily windows; only the 4-state count is genuinely from it. Cell 3 cites a BIC grid search on this dataset that cell 5 declares unreliable; spec's "What Was Tried" table (lines 161–170) documents ≥6 configs iterated on the same data. Fix: restate provenance honestly (in-sample experimentation); treat config as snooped when interpreting OOS results.
- [ ] **H-H5 — No significance; headline gap ≈ 1 standard error; strategy trails on total return.** Cell 15 output / README line 67: T ≈ 4y → SE(annualized Sharpe) ≈ 0.66, so the 1.22-vs-0.66 gap is ~1 SE, before removing the lookahead that generated it; one avoided bear market drives everything. Fix: Sharpe CIs (Lo 2002 / block bootstrap), sub-period results, lead with the total-return shortfall.

## MEDIUM

- [ ] **H-M1 — "Walk-forward" is one static split; no refits; label map unverified.** Cells 11–12: fit once on 2016–2021, never refit over 2022–2026 despite the spec's own "re-fit monthly or quarterly" advice (line 184); `model_wf` regime means never printed, so the drawdown-rank Bull/Bear identification on the pre-2022 fit is unchecked; per-obs test log-likelihood collapses (−0.53 train → −1.68 test), uncommented. Fix: actual expanding-window refit with filtered decoding; print per-refit means; report cross-refit label stability.
- [ ] **H-M2 — Overlapping rolling features violate emission independence; "persistence validates the model" is circular.** Cell 4 (20d vol, 60d drawdown change by one point per day); spec line 77 uses diagonal >0.90 as a quality criterion the features guarantee mechanically. No Gaussian-emission diagnostics anywhere. Fix: acknowledge; sanity-check vs a raw-log-return-only HMM.
- [ ] **H-M3 — Sharpe with rf = 0 while ~51% of test days sit in 0%-yield cash during a 4–5% bill era.** Cell 15 sharpe fn; cell 14 credits cash at 0. Two offsetting distortions, neither disclosed: rf omission inflates the low-vol strategy's relative Sharpe; 0% cash credit understates its return. Fix: excess returns over a T-bill series for both legs; credit cash at the bill rate.
- [ ] **H-M4 — Single EM initialization (seed 42), no multi-restart.** Cells 7, 12: convergence checked (good) but local optimum ≠ global; spec itself admits run instability ("State numbers shuffle across runs", line 130) without quantifying it. Fix: 20+ seeds, keep best likelihood, report dispersion of assignments and backtest metrics.

## LOW

- [ ] **H-L1** — Cell 2: live `yf.download` each run; back-adjusted closes mutate → recorded outputs unregenerable. `research/data/` exists unused. Fix: snapshot to disk.
- [ ] **H-L2** — Cell 6: `get_label_map` uses `argsort` positionally — correct only while the index is 0..n−1; "Recovery" (+0.0005) vs "Correction" (−0.0004) fitted means barely support the labels driving 1.0-vs-0.0 sizing. Fix: `sort_values().index`; validate each state's mean vector against its label.
- [ ] **H-L3** — Cell 14: same-close execution (regime from close t, trade at close t). Shift direction itself is correct. Note the assumption or lag one extra day as robustness.

---

# Platform (`backend/`, `web/`, `research/monte_carlo.ipynb`, docs)

## CRITICAL

- [ ] **P-C1 — Portfolio weights applied to raw price levels.** `backend/engine/portfolio.py:25`: `portfolio_paths = price_paths @ weights` — weights buy *shares* proportional to weight, so the highest-priced asset dominates. **[verified by execution]**: asset A +100% ($10→$20), asset B flat ($1000), 50/50 → engine returns +0.99%; correct is +50%. Every downstream metric inherits this whenever prices differ. Fix: `portfolio_paths = (price_paths / price_paths[:, 0:1, :]) @ weights`.

## HIGH

- [ ] **P-H1 — Unbounded simulation params + `acks_late` = OOM redelivery loop.** `backend/api/schemas.py:5-16` (no bounds on `n_sims`, `n_steps`, `n_samples`, `alpha`, tickers, dates); `gbm.py:22` allocates ≈ 3 × n_sims·n_steps·n_assets·8 bytes; `backend/celery.py:17` `task_acks_late=True` → OOM-killed worker never acks, poison task redelivers forever. Fix: pydantic `Field` bounds (`n_sims ≤ 100_000`, `n_steps ≤ 10_000`, `0 < alpha < 1`, `min_length=1` tickers, `start < end` validator) + total-array-size cap in the pipeline.
- [ ] **P-H2 — No random seed anywhere; contradicts "reproducibility over speed".** `gbm.py:22`, `projection.py:30`, schema has no seed field; identical requests → different numbers; `worker_concurrency=2` shares global RNG state so `np.random.seed()` alone would be unsafe; notebook prototype seeds but production regressed. Fix: optional `seed` in `SimulationRequest`, thread a `np.random.default_rng(seed)` Generator through `simulate_gbm`/`sample_paths`, echo seed in result.
- [ ] **P-H3 — Frontend ships `BRK.B`; yfinance needs `BRK-B`.** `web/app/monte-carlo/page.tsx:47`; **[verified by execution]**: the all-NaN column makes `ffill().dropna()` in `engine/data.py:13-22` drop every row → `ValueError: No valid data returned` → whole job fails, UI shows nothing (see P-M5/P-M6). Fix: `BRK-B` (or symbol mapping); drop all-NaN columns with a per-ticker error instead of nuking all rows.
- [ ] **P-H4 — `pickle.loads` from an unauthenticated Redis published on the host.** `services/cache.py:23,31` + docker-compose `ports: "6379:6379"`, no password: anything reaching 6379 can plant a crafted pickle → arbitrary code execution in the worker. DECISIONS.md accepted pickle "for a local cache"; publishing the port breaks that assumption. Fix: stop publishing the port (compose-network only) or require auth; prefer non-executable serialization (parquet/JSON-split).

## MEDIUM

- [ ] **P-M1 — Notebook portfolio math differently wrong.** `monte_carlo.ipynb` cell 4: `port_log_returns = asset_log_returns @ weights` is a weighted geometric mean — matches neither daily-rebalanced nor buy-and-hold semantics, and disagrees with the engine's (also wrong) convention. Fix: weight simple returns, or buy-and-hold on normalized prices.
- [ ] **P-M2 — PathChart x-axis off-by-two; band polygon extends past the y-axis.** `web/app/monte-carlo/PathChart.tsx:68,78`: paths have `n_steps+1` points but `xScale` divides by `nSteps−1`; reversed lower band ends at `xScale(−1)`. Fix: scale by `path.length − 1`; index the reversed band symmetrically.
- [ ] **P-M3 — `confidence_bands(alpha=0.95)` returns a 90% interval.** `engine/projection.py:16-21` (P5–P95); same `req.alpha` means "5% tail" for VaR (correct) and should mean 2.5/97.5 bounds for a true 95% band. UI legend honestly says P5/P95; docs say "confidence bands". Also: projection.py lacks docstrings. Fix: `(1±alpha)/2` percentiles or rename to percentile bounds.
- [ ] **P-M4 — Cache silently self-disables.** `services/cache.py:13,24-38`: 100ms `socket_timeout` + catch-all `except: return None` → any latency = permanent invisible cache miss re-hitting rate-limited yfinance; `retry_on_timeout=True` retries into the same budget; size log reports bytes as KB; `set()` shadows builtin. Fix: 2–5s timeout, warning-level counter/alerting, fix size math.
- [ ] **P-M5 — Failed jobs leak raw exception text, which the frontend then discards.** `api/main.py:52-57` returns `str(result.result)` verbatim; `page.tsx:153-154` ignores `error` entirely. Also: unknown/expired job IDs return Celery `PENDING` (frontend polls forever); Celery default `result_expires` is 24h, so the spec's "No TTL on results" claim (`docs/specs/2026-03-30-celery-integration.md:48`) is wrong. Fix: sanitized error categories, render `data.error`, treat long-PENDING/unknown ids as failed.
- [ ] **P-M6 — Polling has no error handling; one transient fetch error wedges the UI in "loading" forever.** `page.tsx:144-160`: async `poll()` un-awaited, no try/catch, no max-poll cap. Fix: try/catch with bounded retries + terminal timeout.
- [ ] **P-M7 — `engine/data.py` does network I/O in the layer defined as "pure computation, no I/O".** `data.py:13` (yfinance download) violates CLAUDE.md and ARCHITECTURE.md:65; `interval` is silently hardcoded `'1d'` (cache key omitting interval is only safe because of this). Fix: move to `services/`, document that request `interval` controls step size only.
- [ ] **P-M8 — ARCHITECTURE.md / ROADMAP.md / DECISIONS.md describe a pre-Celery codebase.** They claim `POST /simulate`, a `runtime/` package, "Celery not wired — Not started", "No Docker" — contradicted by `/jobs` endpoints, `pipelines/`+`services/`, wired Celery, committed Dockerfile/compose (README is correct). Project CLAUDE.md also still references `backend/runtime/`. Minor: Celery spec pins 5.4.0 vs installed 5.6.2; spec says Python 3.12-slim vs Dockerfile 3.13-slim. Fix: sweep docs from the Celery spec's accurate "After" tree.

## LOW

- [ ] **P-L1** — Sharpe/VaR conventions inconsistent between `engine/risk.py:100-103` (linear per-step mean annualization, signed-decimal VaR) and `monte_carlo.ipynb` cell 5 (per-path CAGR, positive dollar-loss VaR). Both defensible individually; neither documented. Core VaR/CVaR/MDD math itself verified correct.
- [ ] **P-L2** — `portfolio.py:21-22` accepts long-short weights (sum-to-1 only); negative portfolio values → fractional power of negative → NaN CAGRs → invalid JSON. Fix: require `weights >= 0` or handle explicitly.
- [ ] **P-L3** — `page.tsx:74,108`: exact-float `totalAllocation === 100` gate (backend uses `np.isclose`); also `PathChart` reads *current* form inputs (`page.tsx:404`) so editing nSteps/alpha after a run rescales/relabels the old chart without rerunning.
- [ ] **P-L4** — Service Docker images install the full research/dev freeze (debugpy, ipykernel, matplotlib, statsmodels, arch). Split requirements.
- [ ] **P-L5** — `web/app/page.tsx` is untouched create-next-app boilerplate with no link to `/monte-carlo`; orphaned `backend/engine/__pycache__/exceptions.cpython-313.pyc` for a deleted module.

---

## Suggested fix order (recommendation, 2026-07-07)

1. Correct false claims in specs/README (H-H1, V-H1) — actively misleading, zero-risk edits.
2. P-C1 portfolio fix — one line, hand-verifiable.
3. H-C1 (filtered decoding) and V-C1 (append-before-forecast), then re-run both studies; all downstream conclusions are pending until then.
4. V-C2/V-C3 is a redesign decision (term-structure study vs. real-instrument backtest), not a patch — decide direction before touching it.
