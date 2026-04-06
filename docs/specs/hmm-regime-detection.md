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

### Chosen config (BIC grid search winner, 2018–2026 data)
```python
vol_window      = 20   # log return std over 20 days
drawdown_window = 60   # rolling max over 60 days (~1 quarter)
n_components    = 4    # number of hidden states
feature_cols    = ['log_return', 'rolling_vol', 'drawdown']
```

### Grid search setup
- Searched: `sma_window ∈ [1,5,10,20]`, `vol_window ∈ [5,10,20]`, `dd_window ∈ [30,45,60]`, `n_components ∈ [3,4]`
- Metric: BIC (lower = better)
- `sma_window=1` = raw log return (same thing, different name)
- Grid search consistently favored `vol_window=20`, `dd_window=60`

### BIC formula (correct)
```python
n_features = X.shape[1]
k = nc * (nc - 1) + nc * n_features + nc * n_features * (n_features + 1) // 2
n = len(X_scaled)
ll = model.score(X_scaled)  # already total LL, not per-sample
bic = k * np.log(n) - 2 * ll
```

**Common bug:** `model.score()` returns total log-likelihood. Do not multiply by `n` again.

**BIC limitation:** Assumes IID observations. HMM data is sequential/correlated, so effective sample size < n. BIC tends to slightly overestimate optimal n_components. Use domain knowledge to constrain n_components to [3, 4] and let BIC choose windows only.

---

## Regime Labels (4-state model)

Based on inverse-transformed `model.means_`:

| State | return | vol | drawdown | Label |
|-------|--------|-----|----------|-------|
| Bull | highest positive | lowest | near zero | Steady uptrend, near ATH |
| Chop | mildly negative | moderate | moderate | Directionless, no trend |
| Recovery | high positive | moderate | mild | Sharp bounce off bottom |
| Bear | negative | highest | deep (-13%+) | Sustained drawdown |

**State numbers shuffle across runs.** Always re-derive labels from `model.means_` after fitting. Use `scaler.inverse_transform(model.means_)` to get values in original feature space.

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

---

## Practical Use

The regime signal is useful for **portfolio-level risk management and position sizing**, not intraday timing:

- **Bull + Recovery** → full position / long bias
- **Chop** → reduce size, wait for trend
- **Bear** → defensive, hedge, or flat

For live deployment:
1. Use `model.predict_proba(X)` for soft regime probabilities (more useful than hard labels)
2. Re-fit on expanding window monthly or quarterly
3. Track regime transition probability as a risk signal

---

## Notebook Location

`research/hmm.ipynb`

Cell order:
1. Imports
2. Data loading (`close_prices`)
3. Grid search (BIC over window params)
4. Feature engineering
5. HMM fit + predict
6. Regime interpretation (`model.means_`, transition matrix)
7. Duration analysis + visualization
