# VRP Tail-Conditional Entry (v2) — Research Spec

**Status:** executed 2026-08-04, single OOS pass. Supersedes `vrp-arma-signal.md` (v1), which remains in the repo as the rough draft.
**Notebook:** `research/vrp_tail_v2.ipynb`
**Data:** `research/data/spy_vix_1993_2026.csv` (yfinance snapshot taken 2026-08-03; SPY auto-adjusted close + ^VIX, 8,432 rows, 1993-02-01 → 2026-07-31).

---

## Overview

**Core question:** does conditioning information available at entry reduce the *left tail* of short-variance payoffs, and at what cost in premium?

This reframes v1. v1 asked whether ARMA could forecast the VRP series better than naive persistence — a model bake-off. v2 asks the economically load-bearing question instead: short variance earns a small premium most months and gives it back violently in a few, so the tail is the whole business.

---

## Why v2 exists rather than a v1 patch

The 2026-07-07 adversarial audits (`docs/audits/`) found two classes of problem in v1. The fixable class (walk-forward off-by-one, no significance testing, AIC corner solution, mislabeled CVaR) would have justified a patch. The structural class did not:

- **V-C2, horizon mismatch.** v1's VRP compared 30-calendar-day implied vol (VIX) against **1-day-ahead** GARCH conditional vol. Under vol mean reversion the 30-day expectation exceeds the 1-day estimate on most days even with zero risk premium, so v1's level statistics (82% of days positive, ~3 vol points mean) mixed genuine premium with a term-structure artifact in unknown proportion. The forecast target itself was mis-defined, so no amount of model quality could rescue the study.
- **V-C3, the payoff was not a payoff.** v1 summed spread *levels* (`cumsum` of VIX − GARCH vol), which corresponds to no position in any instrument; and because the GARCH leg was known at decision time, "predicting the sign" was partly tautological.

Decision (2026-08-04): start a new notebook with corrected definitions rather than retrofit v1 — cleaner provenance, and v1 stays legible as the draft the audits describe.

---

## Design decisions

### Payoff: synthetic 30-day variance swap

```python
payoff_t = iv2_t - fwd_rv2_t        # IV² − realized variance over t+1 … t+21
```

**Decision:** define the traded object as a variance-swap seller's settlement — strike `VIX²ₜ`, settled against annualized realized variance of SPY log returns over the next 21 trading days.

**Why:** it fixes V-C2 and V-C3 with one definition. Both legs now refer to the same forward window, and the quantity is the settlement of an actual contract type rather than a sum of spread levels. VIX² is the option market's expected 30-day variance by construction (CBOE's 1/K²-weighted strip *is* the variance-swap replication), so no separate strike source is needed. It also connects to the economics: a delta-hedged short option position earns approximately IV² − RV², so this is the distilled form of what VRP harvesting actually pays.

**Trade-off / limits:** VIX² is a *proxy* for an executed strike — it ignores replication error, discrete strikes, bid-ask, and the practical costs of running an options book (discrete rebalancing, gaps, financing). 30 calendar days ≈ 21 trading days is an approximation. This is a payoff-proxy study, one step short of an instrument backtest.

**Why variance units, not vol:** variance is additive across days (a window's variance is the average of its daily variances); vol is not. Contracts settle in variance for the same reason. Realized variance uses the un-demeaned sum of squared log returns — the contract convention, and at a 21-day horizon the sample mean is ~6× noisier than the drift it would remove.

### Signal leg: multi-step GARCH, matched horizon

```python
E[σ²_{t+h}] = σ̄² + (α+β)^(h-1) · (σ²_{t+1|t} − σ̄²)     # averaged over h = 1..21
evrp_t = iv2_t - egarch_fc_t
```

**Decision:** GARCH(1,1)-t, zero mean, refit each January on an expanding window; closed-form multi-step forecast averaged over the 21-day horizon.

**Why:** the ex-ante quantity must match VIX's horizon (an average over the window, not a point at day 21) and must be causal. Annual refits address audit finding V-H4 (v1 froze near-IGARCH parameters and recursed them 1,002 days). The closed form avoids simulation; forecast accuracy decays with horizon by decaying *toward the long-run mean*, which is the honest behavior under fading information.

**Trade-off:** GARCH(1,1) carries one state variable, so its term structure can only interpolate between today's filtered variance and the long-run mean. Richer specs (two-component GARCH, HAR, rough vol) would produce more structured curves; not explored.

### Conditioning rules: fixed thresholds, no fitted classifier

**Decision:** three candidate danger flags, each a fixed quantile of its *train-period* distribution — GARCH 21-day vol forecast above train q90; ex-ante VRP below train q20; 5-day/63-day realized vol ratio above train q90 (≈1.43).

**Why:** with ~10 independent tail episodes in the sample, a fitted classifier would overfit the very events it is meant to generalize across. Thresholds frozen from train are auditable, have no OOS-tunable parameters, and make the result hard to attribute to search.

**Trade-off:** thresholds were chosen once at conventional quantiles and not swept — but also not validated on a second holdout. Treat the specific magnitudes as one pass, not as tuned-and-confirmed.

### ARMA dropped

**Decision:** no ARMA in v2.

**Why:** re-running v1's walk-forward with the off-by-one corrected (verified 2026-07-24, recorded in the Fable audit under V-C1) gives ARMA RMSE 0.0318 vs naive 0.0327, Diebold-Mariano p=0.30 — statistically indistinguishable. Forecasting the premium series is a weak lever. v2 keeps v1's rule as a benchmark row (`v1-rule-evrp>0`) so the comparison is made on evidence rather than by omission.

### Sample extended to 1993

**Decision:** 1993–2026 (train 1993–2009, OOS 2010–2026) instead of v1's 2016–2026.

**Why:** tail inference on v1's window rested on ~2 independent episodes. The long sample contains ~10 (1997, 1998, 2008, 2010, 2011, 2015, 2018 ×2, 2020, 2022), with train covering 1998 and 2008 so thresholds are set on data that has seen real crises.

---

## Results (2026-08-04, single OOS pass 2010–2026, n = 4,148 entries)

| strategy | premium kept | CVaR-5% | tail cut | mean/entry |
|---|---|---|---|---|
| always-in | 100% | −0.1307 | — | +0.0092 |
| v1 rule (ex-ante VRP > 0) | 81.4% | −0.1185 | 9.3% | +0.0093 |
| **skip high RV momentum** | **96.3%** | **−0.0879** | **32.7%** | **+0.0101** |
| combined (3 filters) | 66.4% | −0.0830 | 36.4% | +0.0096 |

**Observations (facts):** the matched-horizon premium is positive out-of-sample (mean +0.0092/entry, 84.5% of entries positive) and survives a 0.5 vol-point strike haircut. The realized-vol-momentum filter cut CVaR-5% by 32.7% while retaining 96.3% of premium. Block bootstrap (21-day circular blocks, B=2000): P(CVaR cut > 0) = 98.1%, CI90 = [2.7%, 53.5%]; the mean-payoff difference CI90 spans zero.

**Inference (one session, one OOS pass):** the defensible claim is *tail reduction at approximately zero premium cost*, not alpha — the mean improvement is not significant. Direction of the tail effect is robust; magnitude is not pinned down, which is expected with ~10 tail episodes.

**Limit of timing:** the filters were out of the market for the three worst entries (24–26 Feb 2020) but still in on 18–21 Feb 2020. Jump onsets precede any trailing-window signal. This is tail *reduction*, not tail *elimination*; residual worst case ≈ −0.67 vs. mean +0.0092.

---

## Known gotchas

- **Overlapping windows.** Daily entries share 20 of 21 payoff days, so the effective sample is far smaller than n=4,148. Mitigated by a non-overlapping check (every 21st day, n=198) and block bootstrap — not eliminated.
- **Train-period ex-ante VRP uses first-refit parameters in-sample.** Mild within-train hindsight for threshold-setting only; never touches OOS (same class as audit V-M2).
- **`fwd_rv2` is settlement-time data.** It is the payoff leg exclusively and must never enter a signal. Any future edit that references it in a rule reintroduces lookahead.
- **Costs are represented only by a strike haircut.** No roll, margin, financing, or liquidity modeling.

## Explicit non-goals

- No options chain, vol surface, or actual variance-swap quotes — VIX² stands in for the strike.
- No listed-instrument backtest (VIX futures, straddles) with roll and execution costs.
- No position sizing, portfolio construction, or leverage.
- No second holdout validating the threshold choices.
- No backend/engine integration. Research notebook only.
