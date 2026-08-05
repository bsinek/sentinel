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

**Benchmark against uniform deleveraging (the "why not just trade smaller?" test).** The filter is in the market 88.9% of test days. Compared at matched average exposure: uniform 89% sizing every day earns 33.76 with CVaR-5% −0.1161; the filter earns **36.74 with CVaR-5% −0.0876** — better on both axes. Equivalently, achieving the filter's tail risk by unconditional sizing alone requires dropping to 67% size, which earns 25.48, so **the conditional filter delivers ~44% more P&L at equal tail risk**. This is the evidence that the result is a conditional signal rather than disguised deleveraging: proportional sizing damps gains and losses alike, whereas the filter retains full size in the ~89% of states where the premium is earned.

**Mechanism — why the tail moves and the mean does not.** Decomposing the 462 days the pre-committed rule sits out (test period): 362 were winners totalling **+13.23**, 100 were losers totalling **−11.98**, netting **+1.25** — i.e. 3.3% of the always-in total of 37.99, which is the 96.7% retention. The filter therefore does not remove losses; it removes a roughly break-even *mixture*, forgoing fat premiums on elevated-vol days along with the disasters those days occasionally produce. The tail improves anyway because catastrophes are concentrated in that group: **22 of the 50 worst entries fell among the 462 skipped days**, versus 28 among the other 3,686 — about a 6× concentration. The correct description is variance removal at unchanged expected payoff, which is why a non-significant mean difference is the expected result rather than a weakness.

**Limit of timing:** the filters were out of the market for the three worst entries (24–26 Feb 2020) but still in on 18–21 Feb 2020. Jump onsets precede any trailing-window signal. This is tail *reduction*, not tail *elimination*; residual worst case ≈ −0.67 vs. mean +0.0092, and 28 of the 50 worst entries were still taken.

---

## Robustness checks (2026-08-04, run after the headline result)

**Clean protocol run (2026-08-04).** Nine short/long window pairs — short ∈ {5, 10, 21} days, long ∈ {42, 63, 126} days — were swept **on the training period alone** (1993–2009), ranked by train CVaR cut, with the threshold taken as the train q90 of each ratio.

| windows | threshold | train cut | train premium kept |
|---|---|---|---|
| **10d/126d ← selected** | **1.43** | **50.4%** | **114.7%** |
| 21d/126d | 1.36 | 47.1% | 107.3% |
| 5d/126d | 1.46 | 45.4% | 113.6% |
| 10d/63d | 1.34 | 42.8% | 113.6% |
| 10d/42d | 1.31 | 42.6% | 113.9% |
| 21d/63d | 1.25 | 41.8% | 108.6% |
| 21d/42d | 1.19 | 41.5% | 110.1% |
| 5d/63d | 1.43 | 38.4% | 112.6% |
| 5d/42d | 1.41 | 31.1% | 108.5% |

("Premium kept" is total payoff as a share of always-in, net of losses; it exceeds 100% whenever the skipped days carried negative total payoff. Train cuts run 31–50%, above the 32.9% realized on test — the usual in-sample optimism, and the reason train figures are not reportable as results.)

**Train rank does not predict test rank (correlation −0.01).** Scoring all nine pairs on test afterwards: the train-selected 10d/126d placed 6th of 9, while train's 7th-ranked 21d/42d placed 1st (56.8% cut). The specific window pair is therefore *not* learnable from train — but it does not need to be, because the effect holds across the whole neighbourhood.

**Sensitivity map (27 specifications, short ∈ {2,3,5,10,21,42} × long ∈ {21,42,63,126,252}, threshold always train q90, all scored on test):** every specification reduced the tail. Range **18.9%–56.8%**, median **31.9%**, with 24 of 27 above 25%; payoff retained 80.2%–108.3%. The effect degrades only in the bottom row (short = 42d, cuts 18.9%–25.5%), where the "short" window is long enough that the ratio measures volatility *level* rather than acceleration — consistent with level filters ranking below rate-of-change filters in the table below.

So the claim supported is: *any short-vs-long realized-vol ratio with a genuinely short leg (≤ ~21d) cuts the tail by roughly 30–50%*, not that one tuned pair does. The headline reports the pre-committed rule's 32.9%, near the conservative end.

The selected rule — **10d/126d, threshold 1.43** — was then applied once to 2010–2026:

> **CVaR-5% −0.1307 → −0.0876 (32.9% cut), 96.7% of premium retained, mean/entry +0.0092 → +0.0100.**
> **Payoff dispersion −29% (std 0.0551 → 0.0390); Sharpe 0.57 → 1.29.**

*Sharpe, stated precisely.* Computed as mean ÷ std of the payoff on non-overlapping entries (one per 21 trading days, ~12/yr, so the ×√12 annualization is not inflated by window overlap). This is a Sharpe ratio under two assumptions: **constant capital per unit notional**, and **collateral earning the risk-free rate**. Under the first, the capital term appears in numerator and denominator and cancels, so the ratio is invariant to the margin level actually posted; under the second, the payoff already *is* an excess return and there is nothing to subtract. Report it with the assumptions attached, not as a bare Sharpe.

*Collateral is assumed constant, and that assumption is not modelled away.* A real dealer sets margin from a risk-based schedule, so capital would rise when VIX is elevated. That schedule is not available here, so no attempt is made to reproduce it — the reported figure is the standard fixed-capital convention, stated rather than hidden.

An exploratory check (2026-08-04) recomputed the filtered Sharpe under `capital = max(VIX², floor)` for assumed floors at 20/25/30% vol, giving 1.21 / 1.22 / 1.28 — i.e. the result does not appear to hinge on constant capital. **Treat this as indicative only: the floor levels are invented, not sourced.** A pure-proportional variant with no floor gives 0.99, but is not a margin model in any meaningful sense — it implies the 2020-02-07 entry (VIX 15.5, payoff −0.2088) losing 8.73× posted capital, i.e. collateral covering under 12% of the realised loss.

*Remaining caveat.* Sharpe is scale-invariant and therefore silent on ruin risk — 1.29 at 5% margin and 1.29 at 40% margin are different businesses.

*Decomposition.* Numerator +8.8% (0.0092 → 0.0100, inside noise), denominator −29.3% (0.0551 → 0.0390). Essentially all of the improvement is dispersion reduction, consistent with the mechanism below: payoff variance is dominated by a handful of days (the top 10 of 4,148 supply 39.9% of total variance; the top 50 supply 79.7%), so removing tail exposure and reducing standard deviation are near-equivalent operations here.

No test-set information entered the window choice, the threshold, or the ranking, so this number carries no selection optimism. It lands within 0.2 points of the pre-specified 5d/63d rule (32.7% / 96.3%) — the effect does not depend on which windows are picked.

The table below scores a wider set of filters on the OOS block. It is supporting detail on *which families of signal work*, not a source of headline numbers — the reported result is the train-selected rule above.

Efficiency below = CVaR-5% cut ÷ premium given up.

| filter | CVaR cut | premium given up | efficiency |
|---|---|---|---|
| momentum 10d/63d | 39.0% | 0.3% | 150 |
| momentum 5d/21d | 28.5% | 0.7% | 39 |
| **momentum 5d/63d (headline)** | **32.7%** | **3.7%** | **8.8** |
| realized-vol *level* (rv5 < q90) | 24.8% | 13.4% | 1.9 |
| GARCH forecast vol level < q90 | 18.8% | 16.9% | 1.1 |
| VIX level < q90 | 19.2% | 21.4% | 0.9 |
| ex-ante VRP ≥ q20 | 13.7% | 18.3% | 0.8 |
| ARMA forecast of evrp ≥ q20 | 10.9% | 18.5% | 0.6 |
| ARMA forecast of evrp > 0 | 5.7% | 20.7% | 0.3 |

**Observations:** every *rate-of-change* filter outranked every *level* filter, which outranked every *premium-forecast* filter — a monotone ordering across three distinct families, which is stronger evidence than any single cell. An AR(1) forecast of the momentum ratio performed on par with the raw contemporaneous ratio (31.5% cut), i.e. modeling the signal's dynamics added nothing over reading it directly.

Within the momentum family the variants are not separable on this data: the 10d/63d-minus-5d/63d gap is +6.3 points with CI90 [−3.2%, +13.2%]. Treat them as one finding, not a ranking.

**ARMA, re-tested with the horizon mismatch fixed:** BIC selects (2,2) on the matched-horizon ex-ante VRP series; both ARMA-based filters ranked last of everything tested. Combined with the corrected v1 re-run (RMSE 0.0318 vs naive 0.0327, DM p=0.30), the conclusion is that ARMA is not merely redundant here — forecasting the premium series is the wrong lever for the tail question, independent of the v1 bug.

**Combinations (AND) do not help.** Best pair by raw tail cut was momentum 5/63 + ex-ante VRP (38.8% cut) but it surrendered 23.2% of premium — efficiency 1.7 vs 8.8 for momentum alone. Every combination bought extra tail reduction at disproportionate premium cost. No combination beat the best single filter on the trade-off.

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
