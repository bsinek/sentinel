# Adversarial Audit — 2026-07-07 12:34 PDT (Claude Opus 4.8)

**Provenance:** Run 2026-07-07 12:34 PDT by Claude Opus 4.8 via three parallel audit subagents (VRP-ARMA, HMM, platform); the platform pass was completed inline after the subagent dropped on an API error. Scope: methodology (lookahead, costs, calibration validity, significance, overfitting) + code correctness. Findings marked **[reproduced]** were re-run from the committed data and numerically confirmed; all others rest on code reading in one session — re-verify before acting on anything surprising.

**Repo state at audit:** commit `36ad14a` (main), plus untracked `research/generate_report.py`.

**Cell references:** notebook findings cite the section heading (`§N`) and the notebook JSON cell-id hash (e.g. cell `845cc6b4`) so they are pinpointable independent of display ordering. VRP repro scripts saved to the session scratchpad (`repro.py`, `repro2.py`).

---

## Verdict summary

- **VRP-ARMA:** the headline conclusion ("naive persistence beats ARMA out-of-sample") is an artifact of an off-by-one in the walk-forward loop (V-C1) — corrected and re-run, ARMA modestly *beats* naive, so the correct read is "indistinguishable," not a defeat of ARMA. On top of that the traded quantity is not a return (V-C2) and the instrument is untradeable and uncosted (V-C3). Report + slide are invalid until fixed.
- **HMM:** the "out-of-sample" backtest decodes regimes with `predict` (Viterbi) / `predict_proba` (smoothed) over the whole test block, so every regime label at day *t* is conditioned on observations after *t* (H-C1/C2) — anticipative by construction, inside the section labeled "no data leakage." Headline Sharpe 1.22 vs 0.66 is invalid until re-run with filtered inference; total return already trails buy-and-hold (H-C3).
- **Platform:** no CRITICAL surfaced in this pass. Engine math checked out where read (GBM log-drift needs no Itô term given how `mu` is estimated; VaR/CVaR/MDD sign conventions correct); the real holes are no RNG seed anywhere (P-H1, contradicts the project's own "reproducibility over speed") and unbounded simulation inputs (P-H2, trivial OOM/DoS). **Known blind spot of this pass:** the multi-asset portfolio aggregation (`portfolio.py`) was not exercised with divergent price levels — treat it as unverified, not verified-correct.
- **Cross-cutting pattern:** reproducibility is absent throughout (live `yfinance auto_adjust=True` in both notebooks + platform, no seed, a committed CSV the HMM notebook never reads); neither signal models costs or a real instrument; both headline results rest on ≈1–2 events (COVID / 2022) with zero significance testing; and both signals assert rigor ("no data leakage") in the exact section the code contradicts.

---

# VRP-ARMA (`research/vrp_arma_signal.ipynb`, `docs/specs/vrp-arma-signal.md`, `research/generate_report.py`)

## CRITICAL

- [ ] **V-C1 — Walk-forward off-by-one reverses the headline: ARMA scored as a 2-step forecast vs naive's 1-step. [reproduced]**
  Location: notebook §9 cell `845cc6b4`; duplicated `research/generate_report.py:143-151`.
  Evidence: the loop calls `current.forecast(steps=1)` **before** `current = current.append([vrp_val], refit=False)`, so `forecasts[i]` = E[VRP_i | data ≤ i−1]; it is then paired with `actuals[i] = oos_vrp[i+1]`, while `naive[i] = oos_vrp[i] → oos_vrp[i+1]` is a proper fresh 1-step rule. `corr(forecasts, v_i)=0.782` vs `corr(forecasts, v_{i+1})=0.649` confirms the forecast targets `v_i`, not `v_{i+1}`.
  Impact: reproduced from the committed CSV — as-coded ARMA RMSE 0.0395 vs naive 0.0323 (matches notebook 0.0399 / 0.0327); corrected alignment gives ARMA **0.0315** vs naive 0.0323, i.e. ARMA *wins*. Directional accuracy 83.1% → 88.1%. The report, the slide, and all six "Key Findings" ("simple persistence beats complex forecasting," "ARMA added noise") are the inverse of the corrected result. Honest caveat: the corrected ~2% edge is inside noise — the defensible conclusion is "ARMA ≈ naive, indistinguishable," still not the shipped narrative.
  Fix: append the day-t observation before forecasting; re-run RMSE + directional accuracy; rewrite every ARMA-vs-naive conclusion in notebook, report, and slide.

- [ ] **V-C2 — "Cumulative VRP captured" is not P&L of any instrument.**
  Location: notebook §10 cell `27ba3c03`; `generate_report.py:227-235` (`always_cum = actual_next[always_in].cumsum()`, labeled "Cumulative VRP captured").
  Mechanism: VRP = `vix_decimal − garch_cond_vol` is a difference of two annualized vols, not a return. `cumsum(VRP)` corresponds to no tradeable position — there is no instrument whose daily P&L equals that spread. The spec's own "Known Gotchas" states *"VRP is a vol spread, not a return,"* then the notebook, report, and slide all plot it as a performance curve and compute CVaR on it.
  Fix: restate §10 outputs as forecast-accuracy diagnostics and strip P&L language, or backtest a real instrument (front VIX future / short-dated straddle) with costs.

- [ ] **V-C3 — Untradeable instrument, zero costs.**
  Location: whole notebook; spec "Explicit Non-Goals" excludes options / variance swaps / VIX futures.
  Mechanism: harvesting VRP requires shorting variance (var swap, straddle+hedge, or short VIX futures) — all explicitly excluded — so the signal has no execution vehicle. No transaction costs, bid-ask, VIX-futures roll/carry (the dominant cost of any short-vol trade), slippage, or financing anywhere.
  Fix: pick an instrument and cost model, or drop all actionability/performance framing and keep it a forecasting study.

## HIGH

- [ ] **V-H1 — Horizon mismatch invalidates the VRP definition: 30-day implied minus 1-day GARCH vol. [reproduced]**
  Location: §6 cell `7dd5b91a` (`df['vrp'] = df['vix_decimal'] - df['garch_cond_vol']`); GARCH vol built §5 cell `0e8ca132` as `(sqrt(cond_var)/100)*sqrt(252)`.
  Mechanism: `^VIX` is 30-calendar-day (≈21 trading-day) forward implied vol; `garch_cond_vol` is the **1-day-ahead** conditional vol merely scaled by √252. A correct VRP compares 30-day implied to a *multi-step* GARCH forecast of average variance over the next ≈21 trading days. Because GARCH mean-reverts, part of the reported ~0.029 "premium" is a horizon/term artifact. Verified annualized means: VIX 0.185, GARCH-1d 0.156, 21d-realized 0.149. (Also mislabeled: it's a *volatility* spread, not a "variance risk premium.")
  Fix: rebuild the realized leg as the GARCH-implied average vol over the matched 21-trading-day forward horizon; restate all level statistics.

- [ ] **V-H2 — AIC selected the grid corner → self-inflicted overfit; BIC disagrees. [reproduced]**
  Location: §8 cell `91812c26`, grid `p,q ∈ {0..3}`; `arma_fit = ARIMA(train_vrp, order=(p_best,0,q_best))`.
  Evidence: AIC selects **(3,3)** — the maximum order in the grid, the classic "grid too small" signature; BIC selects **(2,0)**. In the SARIMAX summary `ma.L1` is insignificant (p=0.139) and residual heteroskedasticity is significant (Prob(H)=0.00, JB p=0.00), so the OPG standard errors — including the `const` t-stat driving the signal — are unreliable.
  Impact: reporting the AIC corner-solution's OOS failure as a lesson about "complexity" is backwards — the complexity was chosen by the search design, not discovered.
  Fix: select by BIC or train/validation; widen or defend the grid; test squared residuals; check convergence flags.

- [ ] **V-H3 — No statistical significance; the OOS sample is ≈2 independent events.**
  Location: §9–§11; `generate_report.py` metrics.
  Mechanism: hit rates, RMSE, CVaR are point estimates with no CIs, no bootstrap, no Diebold-Mariano / paired test of the ARMA−naive RMSE difference. VRP is ~0.99-autocorrelated, so the 1002 OOS points are massively overlapping; the notebook itself says the loss tail is "dominated by two discrete events" (late-2022, early-2025). Any "dominates on every metric" claim over n≈2 independent episodes is statistically empty.
  Fix: DM test on RMSE, paired test on disagreement days, block-bootstrap CIs; report effective independent-episode count.

- [ ] **V-H4 — Near-IGARCH params frozen and recursed 1002 steps. [reproduced]**
  Location: §5 cell `6d9cd64d` (α+β = 0.9937 reproduced) and cell `0e8ca132` (fixed-param OOS recursion).
  Mechanism: α+β ≈ 0.994 is near-unit-root; the unconditional variance `omega/(1−α−β)` is extremely sensitive to the estimates. Freezing COVID-dominated (2016–2021 train) params and recursing deterministically for four OOS years makes every OOS VRP value fragile to the train window; no sensitivity to split date shown.
  Fix: rolling-refit stability check, or at minimum a sensitivity analysis across train windows / split dates.

## MEDIUM

- [ ] **V-M1 — The 92% "hit rate" is mechanical, not skill.** §10 cell `27ba3c03`, `hit_rate = (vrp_in > 0).mean()`. VRP>0 on ~81% of days and is strongly positively autocorrelated, so `P(VRP[t+1]>0 | VRP[t]>0)` is near-certain by persistence alone. Presenting it as the strategy's virtue dresses up a tautology. Fix: benchmark against the unconditional positive rate; report skill above persistence.
- [ ] **V-M2 — In-sample GARCH params leak into the train VRP that ARMA fits.** §5 cell `6d9cd64d`: `garch_vol_train` is fit on the full train window, so `train_vrp` carries mild within-train hindsight. Does *not* leak into OOS (params frozen before test). Fix: note it; use a causal/expanding train-vol construction for rigor.
- [ ] **V-M3 — Single split presented as a controlled experiment; conclusion partly circular.** §3 cell `5a1f255b` `TRAIN_END='2022-01-01'`. One split at a boundary chosen *because* it's a "natural structural break," then the finding is "models don't generalize across the break." No walk-forward CV / rolling origin / split-date robustness. Fix: rolling-origin CV; separate "ARMA overfits" from "this window was adverse."
- [ ] **V-M4 — `mean='Zero'` GARCH + COVID-dominated training.** §5 cell `6d9cd64d`. Zero-mean on daily SPY (train drift ≈ +6bp/day) inflates conditional variance and depresses VRP (unstated); the train set contains the 2020 crash, so the Student-t / α / near-unit-root persistence are dominated by one event then extrapolated across a calmer OOS regime. Fix: state the mean assumption; sensitivity to constant-mean and to excluding 2020.

## LOW

- [ ] **V-L1** — §4 markdown cell `eef46b04`: "data spans all three VIX regimes ... confirming there is no regime bias" — spanning regimes is not evidence of no bias; over-asserted.
- [ ] **V-L2** — §3 cell `5a1f255b`: `rolling(21).std()` uses ddof=1 (fine) and isn't used in the signal — worth noting the notebook *avoids* the common rolling-window look-ahead here.
- [ ] **V-L3** — Terminology: report title and slide say "Variance Risk Premium" while computing a volatility spread (see V-H1).
- [ ] **V-L4** — `generate_report.py` writes to `~/Desktop`; notebook links to an `htmlpreview.github.io/...bsinek/sentinel...` URL — reproducibility of the published artifacts depends on a manual copy step not in the repo.

**Genuinely sound (VRP):** data hygiene is clean (pinned CSV — 2514 rows, 2016-01-04→2025-12-31, no NaNs/gaps/dupes); using GARCH conditional vol instead of a 21-day rolling window correctly avoids mechanical ACF inflation; the GARCH OOS recursion itself is causal (`cond_var[i]` uses `test_returns[i-1]`, not `[i]`).

---

# HMM (`research/hmm.ipynb`, `docs/specs/hmm-regime-detection.md`)

## CRITICAL

- [ ] **H-C1 — Viterbi lookahead in the "out-of-sample" backtest, inside the section labeled "no data leakage."**
  Location: notebook cell 12 (`85317d7e`): `test_regimes = pd.Series(model_wf.predict(X_test), index=feat_test.index).map(label_map_wf)`; consumed by the backtest in cells 14–15.
  Mechanism: hmmlearn `GaussianHMM.predict()` is **Viterbi decoding** — it returns the single most-likely *global* state path over the entire `X_test` block (all of 2022–2026 passed as one array), so the label at day *t* is conditioned on observations *t+1…T*. The backtest trades `positions.shift(1)`, but lagging the *action* one bar does nothing when the *label itself* already saw four years ahead. This sits directly under spec line 226 ("no data leakage"). The only tradeable object — the *filtered* state `P(state_t | obs ≤ t)` from a model trained only on data ≤ t — is never computed.
  Impact: makes the headline "Sharpe 1.22 vs 0.66, MaxDD −6.42% vs −24.47%" (cell 15) invalid as an OOS claim; near the right edge the decoded path revises as new bars arrive (classic HMM edge flicker), so realized performance collapses toward buy-and-hold.
  Fix: filtered decoding — at each t decode only `X_test[:t+1]` (or run an incremental forward recursion) on a model trained only on data ≤ t; trade on the last filtered state; re-run everything downstream.
  **[fixed + verified by execution 2026-08-05]** Mechanism confirmed from `hmmlearn/base.py` (`predict` -> Viterbi; `predict_proba` -> `forward_log` + `backward_log`, posteriors = `fwdlattice + bwdlattice`) and demonstrated with frozen parameters: 2022-01-05 decodes Recovery from data up to that day, flips to Correction once one later day is visible. 61 of 1003 test days differ. Notebook now decodes causally. Corrected: Sharpe **0.92** vs 0.66, MaxDD **-10.94%** vs -24.47%, total 31.10% vs 50.91%. This audit predicted performance would "collapse toward buy-and-hold" — partially borne out: total return does trail, but risk-adjusted still leads. Costs and refits remain unaddressed.

- [ ] **H-C2 — Soft-probability variant stacks a second lookahead (smoothed posterior).**
  Location: cells 10/12 (`proba = model.predict_proba(...)`, `proba_wf = model_wf.predict_proba(X_test)`), consumed cell 16 (`7f540a43`): `bullish_prob = proba_wf_smooth['Bull'] + proba_wf_smooth['Recovery']; strategy_returns_soft = (bullish_prob.shift(1) * spy_returns)`.
  Mechanism: `predict_proba` returns the forward-**backward smoothed** posterior `γ_t = P(state_t | all obs)` — future-dependent by construction — then further trailing-averaged, then `shift(1)`. Lookahead on lookahead. The tradeable quantity is the *filtered* posterior `α_t = P(state_t | obs ≤ t)`, never computed.
  Impact: the spec's conclusion "soft sizing is inferior (0.91 vs 1.22)" (line 199) compares two contaminated backtests; the "hard beats soft" narrative collapses.
  Fix: recompute both variants on unsmoothed *filtered* posteriors with costs before comparing.
  **[fixed 2026-08-05, costs still absent]** Both variants now run on unsmoothed filtered posteriors: soft Sharpe 0.92 / MaxDD -9.85% / total 30.78% vs hard 0.92 / -10.94% / 31.10%. The "hard beats soft" narrative did collapse as predicted — they tie. Costs still not modeled, so the comparison remains incomplete.

- [ ] **H-C3 — The "alpha" is one avoided event; total return trails buy-and-hold.**
  Location: cell 15 (`5a3c4b2b`) output: Strategy total return **43.32% < benchmark 50.91%**; Sharpe 1.22 vs 0.66; MaxDD −6.42% vs −24.47%. Cell 9 shows only **6 Bear episodes in the 10-year in-sample**.
  Mechanism: the entire outperformance is drawdown avoidance (being flat through 2022) — a single macro bet, effective N≈1, no CI can exclude zero. Framing note: comparing a part-cash strategy's Sharpe to a fully-invested benchmark's Sharpe is not apples-to-apples, and once H-C1's lookahead is removed the timing that produced the drawdown avoidance is not achievable.
  Fix: bootstrap Sharpe CIs (Lo 2002 / block bootstrap), report sub-periods, count independent regime episodes, lead with the total-return shortfall.

## HIGH

- [ ] **H-H1 — In-sample regime map fit on the full 2016–2026 sample, then "detected" historically.** Cell 7 (`60a0da42`): `model.fit(X_scaled)` on all data, then `predict(X_scaled)` Viterbi over everything; the transition matrix (diag > 0.90) is then cited as "validation" (spec lines 77, 145) — circular. Fix: expanding-window fits; stop using in-sample persistence as evidence of quality.
- [ ] **H-H2 — Position→action mapping chosen with hindsight.** Cell 14 (`8ae8ef36`): `position_sizes = {'Bull':1.0,'Recovery':1.0,'Correction':0.0,'Bear':0.0}` — which regimes get 1.0 vs 0.0 is decided knowing after the fact that being flat in drawdowns paid off; no ex-ante rule, no CV of the mapping. Fix: define the mapping from train-only regime statistics; validate out-of-sample.
- [ ] **H-H3 — Zero costs on a regime-switching signal.** Cells 14–15: no cost term anywhere. Spec line 220 admits "Bull/Recovery oscillation on daily data"; whipsaw is only invisible because both Bull and Recovery map to 1.0 (a coincidence of H-H2's hindsight mapping). Any Correction↔Bull flip is a full 0→1 round-trip charged nothing. Fix: compute turnover; apply per-switch costs to both variants.
- [ ] **H-H4 — "Walk-forward" is one static holdout; model never refit.** Cell 12: single split at `'2022-01-01'`, `model_wf.fit(X_train)` once, then decode four years in one shot — the opposite of the spec's own "refit monthly" advice (line 184). By late 2025 the model is 4 years stale. Fix: expanding/rolling refit with filtered decoding at each step.
- [ ] **H-H5 — Non-reproducible source; the committed CSV (with VIX) is never read.** Cell 2 (`715087d9`): live `yf.download('SPY', ..., auto_adjust=True)` — adjusted closes restate over time, so reruns give different regimes. `research/data/spy_vix_2016_2026.csv` (2514 rows, contains a `^VIX` column) is never read by the notebook (no `read_csv`), and VIX — the single most obvious regime feature — sits unused. Code and committed artifact disagree about what the data is. Fix: freeze the CSV as the source; either use VIX or justify dropping it.

## MEDIUM

- [ ] **H-M1 — `n_components=4` imported from the wrong literature; BIC self-contradiction.** Guidolin & Timmermann (2007) fit *monthly multi-asset* returns; this applies the 4-state taxonomy to *daily single-asset* SPY. Cell 3 (`bbba778a`) says windows were "confirmed by BIC grid search on this dataset" while spec lines 111/169 say BIC was removed as unreliable — the notebook and spec contradict each other. Spec line 220 admits 4 states can't separate Bull/Recovery on daily data yet keeps the order. Fix: restate provenance honestly (in-sample experimentation); justify the state count on this data or reduce it.
- [ ] **H-M2 — Single EM seed; non-convexity unaddressed.** Cells 7 & 12: `random_state=42`, one fit each. Baum-Welch is non-convex and init-sensitive; spec line 130 itself admits "state numbers shuffle across runs" without quantifying it. Fix: 20+ seeds, keep best likelihood, report dispersion of state means / transition matrix / backtest metrics.
- [ ] **H-M3 — Forced 4-label assignment regardless of whether 4 regimes exist.** Cell 6 (`650a0b0e`): `get_label_map` `argsort()`s state means by drawdown and hands out Bear/Correction/Recovery/Bull positionally; always emits exactly those four even when two states are near-degenerate (which the spec admits), and a tiny fit perturbation swaps labels, so the train-derived `label_map_wf` may not correspond to the test states. Fix: validate each state's mean vector against its label; handle degeneracy explicitly.
- [ ] **H-M4 — Feature/return inconsistencies + mildly wrong drawdown formula.** Cell 4 (`03da4a55`): `drawdowns = (close - rolling_max) / close` divides by current close, not the peak; features use **log** returns while the backtest P&L uses simple `pct_change()` (cell 14) — internally inconsistent. Fix: divide drawdown by the running peak; use one return convention throughout.

**Genuinely sound (HMM):** the scaler is fit on train only (cell 12: `scaler_wf.fit_transform(feat_train)` then `.transform(X_test)`) — that leakage vector is closed; feature construction is causal (trailing `.rolling()` windows, no forward peeking — the leakage is entirely in the *decoding*); labels are re-derived per fit via `get_label_map` rather than hardcoding state indices, the correct handling of label-switching; going to cash rather than short (spec line 241) and lagging the action are the right risk-conservative instincts (just defeated by H-C1).

---

# Platform (`backend/`, docs)

_No CRITICAL surfaced in this pass. **Blind spot:** `backend/engine/portfolio.py` multi-asset aggregation was not exercised with divergent price levels — unverified, not verified-correct._

## HIGH

- [ ] **P-H1 — No RNG seed anywhere; contradicts "reproducibility over speed."** `backend/engine/gbm.py:22` (`np.random.normal(...)`) and `backend/engine/projection.py:30` (`np.random.choice(...)`) use the global RNG with no seed; `SimulationRequest` (`backend/api/schemas.py`) has no `seed` field. Identical requests return different metrics; no run is reproducible. Directly violates CLAUDE.md ("Research-first infrastructure — reproducibility over speed"). Note: `worker_concurrency=2` shares global RNG state, so a bare `np.random.seed()` would be unsafe. Fix: optional `seed` in the request; thread a `np.random.default_rng(seed)` Generator through `simulate_gbm`/`sample_paths`; echo the seed in the result.
- [ ] **P-H2 — Unbounded simulation inputs → trivial OOM/DoS.** `backend/api/schemas.py:5-16`: no `Field` bounds on `n_steps`, `n_sims`, `n_samples`, `alpha`, tickers, or dates. `gbm.py:22` then allocates `np.random.normal(size=(n_sims, n_steps, n_assets))`, so a request with large `n_sims`/`n_steps` kills the worker. `alpha` outside (0,1) reaches `projection.py:18` `np.percentile(norm_paths, alpha*100)` (e.g. `alpha=2` → percentile 200 → error); `risk.py` guards alpha but `projection.py` does not; negative `n_samples` breaks `np.random.choice`. Fix: pydantic `Field` bounds (`n_sims`, `n_steps`, `n_samples` caps; `0 < alpha < 1`; `min_length=1` tickers; `start < end` validator) + a total-array-size cap in the pipeline.

## MEDIUM

- [ ] **P-M1 — `pickle.loads` on Redis payloads = deserialization RCE.** `backend/services/cache.py:23` (`return pickle.loads(raw)`); Redis in `docker-compose.yml` has no auth and publishes `6379:6379`. Anything able to write to that Redis achieves code execution in the worker. Mitigated only by localhost binding. Fix: don't publish the port (compose-network only) or require auth; prefer a non-executable format (parquet / JSON-split) for cached DataFrames.
- [ ] **P-M2 — Engine-purity rule violated.** CLAUDE.md: "Engine modules in `backend/engine/` are pure computation — no I/O, no side effects." `backend/engine/data.py:13` performs network I/O (`yf.download`); additionally `gbm.py`/`projection.py` mutate global NumPy RNG state (hidden side effect). Fix: move `data.py` to `services/`; document that the request `interval` controls step size only.
- [ ] **P-M3 — The `interval` request field is silently disconnected from the data.** `backend/engine/data.py:13` hardcodes `interval='1d'`, so `SimulationRequest.interval` never changes what's fetched, and `estimation.py:16-17` hardcodes `*252`. Selecting `'1mo'` keeps daily data + daily-annualized params but sets `dt=1/12` (`pipelines/simulate.py:22-28`), so `n_steps=252` → a **21-year** projection off daily estimates. The field looks like it controls granularity; it only rescales the horizon. Fix: either fetch at the requested interval and annualize accordingly, or rename/document the field as step-size only.
- [ ] **P-M4 — `ffill().dropna()` biases estimation.** `backend/engine/data.py:19`: forward-fill injects stale zero-return days that bias volatility down and inflate autocorrelation; the following `dropna()` silently discards leading history for any ticker with a later inception date (mismatched-calendar assets lose data with no warning). Fix: align calendars explicitly; surface a per-ticker error rather than dropping rows; avoid ffill for return estimation.

## LOW

- [ ] **P-L1** — `backend/services/cache.py:13`: `socket_timeout=0.1` (100ms) with errors swallowed to `warning` → under any latency blip the cache silently degrades to always-miss, re-hitting rate-limited yfinance, with no surfaced signal; `retry_on_timeout=True` retries into the same tiny budget. Fix: 2–5s timeout; warning-level counter/alerting.
- [ ] **P-L2** — `backend/engine/risk.py:100-103`: Sharpe/vol annualization mixes linear mean-return scaling (`ann_return = mean/dt`) with √t vol scaling — industry-standard but inconsistent; `volatility` pools across sims *and* steps into one `std`. Both defensible; neither documented.
- [ ] **P-L3** — `backend/api/schemas.py`: no `start < end` validation; relies on downstream yfinance returning empty → `ValueError` surfaced as a failed job.

**Genuinely sound (platform):** the GBM math is correct and pre-empts the obvious attack — `mu` is estimated as the mean **log** return (`estimation.py:16`) and used directly as the log-drift (`gbm.py:26`), so no `−½σ²` Itô term is needed (adding one would double-count); Cholesky-based correlated diffusion is right, with a clean error on non-PSD covariance (`gbm.py:17-20`). VaR/CVaR sign conventions and `max_drawdowns` (`risk.py:106-154`) are correct. Compute is properly offloaded to Celery so the API event loop never blocks; CORS is scoped to `localhost:3000` (not wildcard); requirements are fully pinned; the cache fails open.

---

## Suggested fix order (recommendation, 2026-07-07)

1. Correct the false rigor claims in specs/README first (H-C1's "no data leakage", V-C1-adjacent "no lookahead bias") — actively misleading to every future reader, zero-risk edits.
2. V-C1 (append-before-forecast) and H-C1 (filtered decoding), then re-run both studies — every downstream conclusion, report, and slide is pending until then.
3. P-H1 (seed) + P-H2 (input bounds) — small, high-value platform hardening.
4. V-C2/V-C3 and H-C3 are redesign decisions (forecasting-diagnostic vs real-instrument-with-costs), not patches — decide direction before touching them.
5. Independently verify `portfolio.py` multi-asset aggregation with divergent price levels — flagged as an unverified blind spot of this pass.
