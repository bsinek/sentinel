# HMM Regime Detection — Research Spec

## Overview

Market regime detection using a Hidden Markov Model (GaussianHMM) trained on SPY daily price data. The model identifies latent market states (bull, bear, chop, recovery) from observable features derived from price history.

---

## What the Literature Says

### Key Papers

**Hamilton (1989) — "A New Approach to the Economic Analysis of Nonstationary Time Series"**
- The foundational Markov-switching paper. Observable: quarterly log-differenced U.S. real GNP (not equity returns at all — it's a macro business-cycle paper).
- 2 hidden states (expansion / recession). Raw first-differences, no smoothing.
- Established the EM algorithm for Markov-switching estimation. Everything since is built on this.

**Ang & Bekaert (2002) — "International Asset Allocation With Regime Shifts"**
- Monthly continuously compounded excess returns on MSCI country indices (USD).
- 2–3 regimes with regime-dependent mean, variance, and correlation structure.
- Key finding: bear regimes are characterized by high volatility AND high cross-country correlation — diversification breaks down exactly when you need it most.
- Used for asset allocation: optimal portfolio weights shift dramatically across regimes.

**Hardy (2001) — "A Regime-Switching Model of Long-Term Stock Returns"**
- Monthly S&P 500 and TSX 300 returns. Lognormal regime-switching (2 states) fit via MLE.
- Key application: actuarial / insurance use case — pricing guarantees on equity-linked products.
- Showed regime-switching fits long-term return distributions better than single Gaussian.

**Guidolin & Timmermann (2007) — "Asset Allocation Under Multivariate Regime Switching"**
- Monthly excess returns on stocks, bonds, T-bills (CRSP data).
- **4-state model** — most directly relevant to our implementation. States: bull, bear, slow growth, recovery.
- Transition matrix is nearly block-diagonal (regimes are persistent). Bear → recovery → bull path, not Bear → Bull directly.
- Optimal asset allocation derived analytically for each regime. Bull: overweight equity. Bear: overweight bonds/cash.

**Kritzman, Page & Turkington (2012) — "Regime Shifts: Implications for Dynamic Strategies"**
- Different approach: input features are **engineered turbulence measures** (Mahalanobis distance of returns from historical mean/covariance), not raw returns.
- Turbulence = `(r - μ)' Σ⁻¹ (r - μ)` — measures how unusual today's return vector is relative to historical norms.
- Smoothed monthly. High turbulence = stress regime. Straightforward 2-state model.
- Useful framing: you can feed engineered risk features into HMM, not just raw returns. Future extension possibility.

**Ang (NBER w10080) — "How Do Regimes Affect Asset Allocation?"**
- Follow-on to Ang & Bekaert (2002). Same monthly log return methodology.
- Focuses specifically on how optimal portfolio weights change across regimes.
- Key result: ignoring regime shifts leads to significant welfare losses for investors — regime-aware allocation meaningfully outperforms static mean-variance.
- Directly relevant as motivation for why regime detection is worth building.

**Ang (NBER w17182) — "Regime Changes and Financial Markets"** (review paper)
- Survey paper covering the full landscape of regime-switching models in finance.
- Covers equity, fixed income, currency, and commodity applications.
- Good reference if you need to cite the broader field in documentation or write-ups.

**Statistical Jump Model (arxiv 2024) — "Downside Risk Reduction via Statistical Jump Model"**
- Recent alternative to HMM for regime detection. Instead of Gaussian emissions + EM, uses L1 regularization to penalize frequent regime switches directly in the objective function.
- Key advantage over HMM: the minimum dwell time (minimum regime duration) is a tunable parameter, directly solving the fragmentation/zebra-stripe problem we encountered.
- Does not require specifying a transition probability matrix — jumps are penalized by a regularization term λ.
- Worth reading if fragmentation remains a problem after feature tuning. Could replace or complement the HMM approach in Sentinel.
- Arxiv: https://arxiv.org/html/2402.05272v2

### Summary Table

| Paper | Data | Features | States | Key Contribution |
|-------|------|----------|--------|-----------------|
| Hamilton (1989) | Quarterly GNP | Raw log diff | 2 | Founded the framework |
| Ang & Bekaert (2002) | Monthly equity | Raw log returns | 2–3 | Cross-asset allocation, correlation regimes |
| Hardy (2001) | Monthly equity | Raw log returns | 2 | Long-run distributional fit |
| Guidolin & Timmermann (2007) | Monthly multi-asset | Raw log returns | 4 | Multi-asset allocation, 4-state taxonomy |
| Kritzman et al. (2012) | Monthly | Turbulence (engineered) | 2 | Feature engineering approach |

### Consensus on Implementation

**Raw log returns, no SMA smoothing.** Academic work uses monthly data; practitioner implementations (QuantStart etc.) use raw daily log returns. SMA compresses variance and blurs regime transitions — the opposite of what the HMM needs. The HMM's Gaussian emission model handles noise internally via EM.

**Number of states:** 2 states (bull/bear) is the minimum and most stable. 4 states (Guidolin & Timmermann) is the richest academically validated model and maps naturally to bull/bear/chop/recovery. More than 4 states is rarely justified on equity return data.

**Covariance type:** `full` covariance is standard in the literature (regime-dependent correlation structure, not just variance). This is what distinguishes multi-asset regime models — correlations shift across regimes.

**Transition matrix:** In well-fitted models, regimes are highly persistent (diagonal entries >0.90). Transitions follow a path (bear → chop → bull) rather than jumping. A transition matrix with many non-zero off-diagonal entries suggests too many states or poor feature separation.

---

## Features

Three input features derived from daily close prices:

```python
log_returns  = np.log(close / close.shift(1)).dropna()
rolling_vol  = log_returns.rolling(window=vol_window).std()
rolling_max  = close.rolling(window=dd_window).max()
drawdowns    = (close - rolling_max) / close
```

**Feature rationale:**
- `log_return`: Daily directional signal. Raw, not smoothed. Gives the model real-time directionality.
- `rolling_vol`: Volatility regime signal. Distinguishes calm vs stressed markets.
- `drawdown`: Distance from recent peak. Captures cumulative stress / drawdown depth.

**Do not add `sma_return` as a separate feature.** It caused fragmentation (zebra stripes) when used alongside raw returns.

---

## Parameter Decisions

### Chosen config (literature-validated)
```python
vol_window      = 20   # log return std over 20 days — Guidolin & Timmermann (2007)
drawdown_window = 60   # rolling max over 60 days (~1 quarter)
n_components    = 4    # 4 states per Guidolin & Timmermann (2007)
feature_cols    = ['log_return', 'rolling_vol', 'drawdown']
```

Parameters are fixed from the literature, not grid-searched. BIC grid search was explored but removed for two reasons:
- BIC assumes IID observations; HMM data is sequential, so effective sample size < n, causing BIC to overestimate optimal `n_components`
- BIC rewards smoother features (tighter Gaussians) as a statistical artifact — it consistently preferred `sma_window=20` despite SMA causing fragmentation in practice

Grid search on `vol_window` consistently returned `vol_window=20, dd_window=60`, which matches the literature. No reason to grid-search what the papers already tell you.

---

## Regime Labels (4-state model)

Based on inverse-transformed `model.means_`:

| State | return | vol | drawdown | Label |
|-------|--------|-----|----------|-------|
| Bull | highest positive | lowest | near zero | Steady uptrend, near ATH |
| Correction | mildly negative | moderate | moderate | Directionless or shallow pullback |
| Recovery | high positive | moderate | mild | Sharp bounce off bottom |
| Bear | negative | highest | deep (-13%+) | Sustained drawdown |

**State numbers shuffle across runs.** Always re-derive labels from `model.means_` after fitting. Labels are assigned by ranking drawdown depth — most negative drawdown = Bear, least negative = Bull. This is done via `get_label_map()`:

```python
def get_label_map(model_means, scaler, feature_cols) -> dict:
    regime_means = pd.DataFrame(scaler.inverse_transform(model_means), columns=feature_cols)
    sorted_labels = regime_means['drawdown'].argsort()
    return {
        sorted_labels.iloc[0]: 'Bear',
        sorted_labels.iloc[1]: 'Correction',
        sorted_labels.iloc[2]: 'Recovery',
        sorted_labels.iloc[3]: 'Bull',
    }
```

### Transition matrix interpretation
A well-fitted model shows near-diagonal transitions (high self-persistence) and sequential neighbor transitions. States should not jump directly from Bull to Bear or vice versa — they should transition through intermediate states. If you see Bull ↔ Bear direct transitions at >5%, the model is likely unstable or overparameterized.

---

## Known Limitations

**Drawdown lag:** The 60-day rolling max means drawdown stays deeply negative during recovery (price rising but still below 60-day peak). The Bear state captures both the crash AND the early recovery. This is inherent to the feature — a shorter dd_window reduces lag but destabilizes the model.

**SMA lag:** If using sma_return, a 20-day window delays the recovery regime by ~20 days. Raw log_return avoids this.

**In-sample only:** The model is fit and evaluated on the same data. For live use, re-fit periodically (rolling window or expanding window) and track regime probability (`model.predict_proba()`) not just hard labels.

**BIC favors smoothed features:** If you run grid search with sma_windows included, BIC will prefer longer SMA windows because smoother features produce tighter Gaussians. This is a statistical artifact — don't interpret it as validation of smoothing.

---

## What Was Tried and Why It Failed

| Approach | Problem |
|----------|---------|
| `sma_window=20` as sole return feature | Regime fragmentation (Bull avg 1 day). SMA too smooth — no variance for the model to separate bull from chop |
| `sma_return + log_return` together | Still fragmented. Correlated features, plus log_return noise dominates |
| `n_components=5` | States 0 and 1 averaged 3–5 days each. BIC formula was also buggy (hardcoded 3 instead of nc). Even after fix, 5 states produced indistinguishable near-ATH sub-states |
| `vol_window=5` | Too reactive — short-term vol spikes caused frequent false regime switches in bull periods |
| BIC with unconstrained n_components | BIC underpenalizes higher component models for sequential data. Always fix n_components based on domain knowledge (3 or 4), use BIC for window selection only |
| BIC grid search over vol/dd windows | BIC rewards smoother features as an artifact (tighter Gaussians = lower BIC). When sma_windows included, BIC picks the longest SMA — a statistical artifact, not signal. Grid search removed; parameters fixed from Guidolin & Timmermann (2007) instead |

---

## Practical Use

The regime signal is useful for **portfolio-level risk management and position sizing**, not intraday timing:

- **Bull + Recovery** → full position / long bias
- **Correction** → reduce size or hold cash
- **Bear** → defensive, hedge, or flat

For live deployment:
1. Use hard regime labels for position sizing — outperforms soft probabilities when model confidence is high
2. Re-fit on expanding window monthly or quarterly
3. Track regime transition probability as a risk signal

---

## Soft Probabilities

`model.predict_proba(X)` returns a (T, 4) matrix — probability of each regime at each timestep. Note that on a full sequence these are *smoothed* posteriors and are not causal; see Walk-Forward Validation for the filtered version used in any backtest.

For visualization, smooth with a 10-day rolling mean before plotting as a stacked area chart. The smoothing is display-only — do not smooth before feeding to the model or backtest.

**Continuous position sizing (tested, ties the binary rule):**
```python
bullish_prob = proba_wf_df['Bull'] + proba_wf_df['Recovery']   # filtered, unsmoothed
```
Backtested against hard labels on 2022–2026, both on filtered posteriors (2026-08-05 re-run): soft Sharpe 0.92 / MaxDD −9.85% / total 30.78% vs hard 0.92 / −10.94% / 31.10%. The two are effectively tied, with soft giving up a little return for a slightly shallower drawdown — consistent with a high-confidence model (transition diagonal >0.90) whose posteriors sit near 0 or 1 most days, leaving little room for sizing to differ from a binary rule.

Supersedes an earlier claim that soft sizing was inferior (Sharpe 0.91 vs 1.22). That comparison was confounded twice over: the hard variant used leaked full-block Viterbi labels while the soft variant used *smoothed* posteriors, violating this spec's own display-only rule above.

---

## Walk-Forward Validation

Fit on 2016–2021 (pre-2022), decode 2022–2026. Scaler fit on train only.

The train/test split closes *parameter* leakage but not *inference* leakage. hmmlearn's `predict()` runs Viterbi ("the most likely sequence of states, given all emissions") and `predict_proba()` runs forward-backward, forming posteriors as `fwdlattice + bwdlattice` where the backward term is P(observations after *t* | state at *t*) (`hmmlearn/base.py`). Passing either the whole test block lets a label borrow evidence from its own future. Regimes are therefore decoded causally — at each *t*, only `X_test[:t+1]` is visible:

```python
def filtered_posteriors(model, X):
    # last row of predict_proba on a prefix has beta_t = 1 -> filtered, not smoothed
    return np.vstack([model.predict_proba(X[:t + 1])[-1] for t in range(len(X))])
```

```python
split_date = '2022-01-01'
feat_train = features[features.index < split_date]
feat_test  = features[features.index >= split_date]
scaler_wf  = StandardScaler()
X_train    = scaler_wf.fit_transform(feat_train)
X_test     = scaler_wf.transform(feat_test)       # transform only, no fit
model_wf   = GaussianHMM(n_components=4, covariance_type='full', n_iter=1000, random_state=42)
model_wf.fit(X_train)
```

Purpose: confirm that regime structure detected in-sample generalizes to unseen data. If the out-of-sample regimes match the qualitative structure (COVID → Bear, 2021 → Bull, 2022 drawdown → Bear), the model is stable.

**Known issue:** Bull/Recovery oscillation on daily data. The model alternates between these two states during sustained uptrends. This is a state separation problem — on monthly data (as in the literature) the distinction is cleaner. Solutions: merge to 3 states, use soft probabilities as continuous signal, or use Statistical Jump Model. Evaluate impact via backtest before addressing.

---

## Backtest (Out-of-Sample, 2022–2026)

Backtest uses `test_regimes` from walk-forward, decoded causally (see Walk-Forward Validation above). Parameters are fit on train only *and* each day's regime is inferred from data up to that day only.

**Results (2026-08-05 re-run, filtered decoding):**

| | Strategy | Buy-and-hold |
|---|---|---|
| Total return | 31.10% | 50.91% |
| Sharpe (rf = 0) | 0.92 | 0.66 |
| Max drawdown | −10.94% | −24.47% |

Supported claim: the regime filter roughly halves drawdown and raises risk-adjusted return, at a real cost in total return. Not supported: that it beats buy-and-hold outright, or that the Sharpe gap is statistically distinguishable — over ~4 years SE(annualized Sharpe) ≈ 0.5, so 0.92 vs 0.66 is inside noise, and one avoided bear market drives the result.

**Cost sensitivity (2026-08-05):** the binary rule makes 22 position round-trips over the 4-year test window, so costs are close to irrelevant — Sharpe 0.92 → 0.90 → 0.88 → 0.84 at 0 / 2 / 5 / 10 bps per switch (total return 31.10% → 28.22% at 10 bps). Filtered decoding does flicker more than Viterbi, which enforces a globally coherent path: 76 label switches vs 65. That does not translate into more trading here because Bull and Recovery both map to a 1.0 position.

**Still not modeled:** cash is credited at 0% through a 4–5% bill era (this understates the strategy, which sits ~51% in cash, while the rf = 0 Sharpe overstates it — two offsetting distortions, neither quantified); expanding refits (the model is fit once on 2016–2021 and never updated); multi-restart EM (single seed 42).

### Prior result, superseded

An earlier version of this backtest reported Sharpe 1.22 / max drawdown −6.42% / total return 43.32%. Those numbers came from `model_wf.predict(X_test)` on the whole test block — Viterbi over the full sequence, which conditions each day's label on later days (audit finding H-C1). Verified by execution: full-block and causal decoding disagree on 61 of 1003 test days, clustered on regime turns; 2022-01-05 flips from Recovery to Correction as soon as one later day enters the window, which is what put the leaked version in cash at the exact market top.

### Version 1 — Binary Long/Cash

```python
spy_returns = close_prices.loc[feat_test.index].pct_change()
position    = test_regimes.map({'Bull': 1.0, 'Recovery': 1.0, 'Correction': 0.0, 'Bear': 0.0})

# position set at close of day d, applied to return of day d+1
strategy_returns  = (position.shift(1) * spy_returns).dropna()
benchmark_returns = spy_returns.dropna()
```

**Metrics:** total return, annualized Sharpe, max drawdown — compared to buy-and-hold.

**Why cash, not short:** The model was not trained to time short entries. Cash avoids being wrong in two directions; shorting doubles the risk of misclassification. Short could be added as a separate signal once the model is validated.

### Version 2 — Soft Probability Sizing (refinement)

```python
bullish_prob     = proba_wf_df['Bull'] + proba_wf_df['Recovery']   # filtered, unsmoothed
strategy_soft    = (bullish_prob.shift(1) * spy_returns).dropna()
```

Removes cliff edges at transition points. Use this after Version 1 is validated.

---

## Notebook Location

`research/hmm.ipynb`

Cell order:
1. Imports
2. Data loading (`close_prices`, 2016–2026)
3. Feature engineering (`log_return`, `rolling_vol`, `drawdown`)
4. Markdown — 4-state rationale + BIC limitation note
5. `get_label_map()` helper + palette
6. HMM fit + label + regime stats
7. Duration analysis + hard label visualization
8. Soft probability visualization
9. Walk-forward validation (fit pre-2022, predict 2022–2026, hard + soft charts)
10. Backtest (out-of-sample performance vs buy-and-hold)
