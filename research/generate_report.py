"""Generate VRP-ARMA summary report and presentation slide as standalone HTML files."""

import os
import io
import base64
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from scipy.stats import gaussian_kde
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import ConvergenceWarning, ValueWarning
from statsmodels.tsa.arima.model import ARIMA
from arch import arch_model

warnings.simplefilter('ignore', ValueWarning)
warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', FutureWarning)

DARK_BG    = '#111111'
DARK_PANEL = '#1a1a1a'
WHITE      = 'white'
DESKTOP    = os.path.expanduser('~/Desktop')

# ── helpers ──────────────────────────────────────────────────────────────────

def dark_ax(ax):
    ax.set_facecolor(DARK_PANEL)
    ax.tick_params(colors=WHITE)
    ax.xaxis.label.set_color(WHITE)
    ax.yaxis.label.set_color(WHITE)
    ax.title.set_color(WHITE)
    for spine in ax.spines.values():
        spine.set_visible(False)


def plot_vrp_kde(ax, data, title, pos_label='Positive', neg_label='Negative',
                 xlabel='VRP (annualized vol points)'):
    data   = np.asarray(data)
    hit    = (data > 0).mean()
    losses = data[data < 0]
    wins   = data[data > 0]
    cl = losses[losses <= np.percentile(losses, 5)].mean() if len(losses) else np.nan
    cw = wins[wins   >= np.percentile(wins,  95)].mean()  if len(wins)   else np.nan
    x    = np.linspace(data.min(), data.max(), 500)
    y    = gaussian_kde(data, bw_method=0.15)(x)
    peak = y.max()
    ax.plot(x, y, color=WHITE, lw=1.5)
    ax.fill_between(x, y, where=(x >= 0), alpha=0.3, color='#4ade80',
                    label=f'{pos_label} ({hit:.1%})')
    ax.fill_between(x, y, where=(x <  0), alpha=0.3, color='#f87171',
                    label=f'{neg_label} ({1-hit:.1%})')
    ax.axvline(0,  color=WHITE,     lw=0.8, linestyle='--', alpha=0.5)
    ax.axvline(cl, color='#f87171', lw=1.2, linestyle=':',  alpha=0.9)
    ax.axvline(cw, color='#4ade80', lw=1.2, linestyle=':',  alpha=0.9)
    ax.annotate(f'CVaR {cl:.3f}', xy=(cl, 0), xytext=(cl - 0.01, peak * 0.25),
                color='#f87171', fontsize=8, ha='right')
    ax.annotate(f'CVaR {cw:.3f}', xy=(cw, 0), xytext=(cw + 0.01, peak * 0.25),
                color='#4ade80', fontsize=8, ha='left')
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Density')
    ax.legend(facecolor='#222222', labelcolor=WHITE, fontsize=9)
    return cl, cw, hit


def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


# ── data ─────────────────────────────────────────────────────────────────────

print('Loading data...')
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data/spy_vix_2016_2026.csv')
df = pd.read_csv(DATA_PATH, index_col='Date', parse_dates=True)

df['log_return']  = np.log(df['SPY'] / df['SPY'].shift(1))
df['rolling_vol'] = df['log_return'].rolling(21).std() * np.sqrt(252)
df['vix_decimal'] = df['^VIX'] / 100
df.dropna(inplace=True)

TRAIN_END = '2022-01-01'
train = df[df.index < TRAIN_END]
test  = df[df.index >= TRAIN_END]

# ── GARCH ─────────────────────────────────────────────────────────────────────

print('Fitting GARCH...')
res_t = arch_model(train['log_return'] * 100, vol='GARCH', p=1, q=1,
                   mean='Zero', dist='t').fit(disp='off')
params_t = res_t.params
garch_vol_train = (res_t.conditional_volatility / 100) * np.sqrt(252)

omega = params_t['omega']
alpha = params_t['alpha[1]']
beta  = params_t['beta[1]']
last_var   = res_t.conditional_volatility.iloc[-1] ** 2
last_resid = (train['log_return'].iloc[-1] * 100) ** 2

test_returns = (test['log_return'] * 100).values
cond_var = np.zeros(len(test_returns))
for i in range(len(test_returns)):
    cond_var[i] = omega + alpha * last_resid + beta * last_var
    last_resid  = test_returns[i] ** 2
    last_var    = cond_var[i]
garch_vol_test = (np.sqrt(cond_var) / 100) * np.sqrt(252)

df['garch_cond_vol'] = pd.concat([
    pd.Series(garch_vol_train.values, index=train.index),
    pd.Series(garch_vol_test,         index=test.index)
])
df['vrp'] = df['vix_decimal'] - df['garch_cond_vol']
vrp = df['vrp'].dropna()

# ── ARMA ──────────────────────────────────────────────────────────────────────

print('Grid-searching ARMA...')
train_vrp = df.loc[df.index < TRAIN_END, 'vrp'].dropna()
results = []
for p in range(0, 4):
    for q in range(0, 4):
        if p == 0 and q == 0:
            continue
        try:
            m = ARIMA(train_vrp, order=(p, 0, q)).fit()
            results.append({'p': p, 'q': q, 'aic': m.aic})
        except Exception:
            pass
grid = pd.DataFrame(results).sort_values('aic').reset_index(drop=True)
p_best, q_best = int(grid.iloc[0]['p']), int(grid.iloc[0]['q'])
arma_fit = ARIMA(train_vrp, order=(p_best, 0, q_best)).fit()

print(f'Running walk-forward OOS (ARMA({p_best},{q_best}))...')
oos_vrp = df.loc[df.index >= TRAIN_END, 'vrp'].dropna()
forecasts, current = [], arma_fit
for vrp_val in oos_vrp.iloc[:-1]:
    fc = current.forecast(steps=1)
    forecasts.append(float(fc.iloc[0]))
    current = current.append([vrp_val], refit=False)

forecast_index = oos_vrp.index[:-1]
actuals        = oos_vrp.iloc[1:].values
naive          = oos_vrp.iloc[:-1].values

rmse_arma  = np.sqrt(np.mean((np.array(forecasts) - actuals) ** 2))
rmse_naive = np.sqrt(np.mean((naive - actuals) ** 2))

actual_next = pd.Series(actuals, index=forecast_index)
fc_series   = pd.Series(forecasts, index=forecast_index)
always_in   = pd.Series(True, index=forecast_index)
naive_in    = pd.Series(oos_vrp.iloc[:-1].values > 0, index=forecast_index)
arma_in     = fc_series > 0

def backtest_stats(signal, actual_vrp):
    vrp_in   = actual_vrp[signal]
    losses   = vrp_in[vrp_in < 0]
    cvar     = losses[losses <= np.percentile(losses, 5)].mean() if len(losses) else np.nan
    return {
        'days_in':  signal.sum(),
        'hit_rate': (vrp_in > 0).mean(),
        'mean_vrp': vrp_in.mean(),
        'cvar':     cvar,
    }

stats_always = backtest_stats(always_in, actual_next)
stats_naive  = backtest_stats(naive_in,  actual_next)
stats_arma   = backtest_stats(arma_in,   actual_next)


# ── FIGURE 1: VRP over time + distribution ────────────────────────────────────

print('Generating figures...')
fig1, axes = plt.subplots(1, 2, figsize=(16, 5))
fig1.patch.set_facecolor(DARK_BG)
for ax in axes:
    dark_ax(ax)

axes[0].plot(df.index, df['vrp'], color='#fde047', lw=0.8, alpha=0.9)
axes[0].axhline(0, color=WHITE, lw=0.7, linestyle='--', alpha=0.4)
axes[0].fill_between(df.index, 0, df['vrp'],
                     where=(df['vrp'] > 0), alpha=0.2, color='#4ade80',
                     label='Implied vol overpriced (VRP > 0)')
axes[0].fill_between(df.index, 0, df['vrp'],
                     where=(df['vrp'] < 0), alpha=0.2, color='#f87171',
                     label='Implied vol underpriced (VRP < 0)')
axes[0].axvline(pd.Timestamp(TRAIN_END), color='#60a5fa', lw=1, linestyle='--', alpha=0.7)
axes[0].text(pd.Timestamp(TRAIN_END), df['vrp'].max() * 0.85, ' OOS →',
             color='#60a5fa', fontsize=8)
axes[0].set_title('Variance Risk Premium (VRP) — 2016–2026')
axes[0].set_ylabel('VRP (annualized vol points)')
axes[0].legend(facecolor='#222222', labelcolor=WHITE, fontsize=9)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

cl, cw, hit = plot_vrp_kde(
    axes[1], vrp.values, 'VRP Distribution (full period)',
    pos_label='Implied overpriced', neg_label='Implied underpriced',
    xlabel='VRP — vol points (annualized)',
)
fig1.suptitle('Figure 1 — The VRP Signal: VIX Systematically Overprices Realized Volatility',
              color=WHITE, fontsize=11, y=1.01)
fig1.tight_layout()
img1 = fig_to_b64(fig1)


# ── FIGURE 2: Strategy comparison ────────────────────────────────────────────

fig2 = plt.figure(figsize=(18, 9))
fig2.patch.set_facecolor(DARK_BG)
gs = GridSpec(2, 3, figure=fig2, hspace=0.4, wspace=0.3)

ax_cum = fig2.add_subplot(gs[0, :2])
ax_bar = fig2.add_subplot(gs[0, 2])
ax_d1  = fig2.add_subplot(gs[1, 0])
ax_d2  = fig2.add_subplot(gs[1, 1])
ax_d3  = fig2.add_subplot(gs[1, 2])
for ax in [ax_cum, ax_bar, ax_d1, ax_d2, ax_d3]:
    dark_ax(ax)

always_cum = actual_next[always_in].cumsum()
naive_cum  = actual_next[naive_in].cumsum()
arma_cum   = actual_next[arma_in].cumsum()
ax_cum.plot(always_cum.index, always_cum.values, color='#60a5fa', lw=1.5, label='Always-in', alpha=0.8)
ax_cum.plot(naive_cum.index,  naive_cum.values,  color='#a78bfa', lw=1.5, label='Naive binary (VRP > 0 today)')
ax_cum.plot(arma_cum.index,   arma_cum.values,   color='#4ade80', lw=1.5, label=f'ARMA({p_best},{q_best}) timed', alpha=0.8)
ax_cum.axhline(0, color=WHITE, lw=0.6, linestyle='--', alpha=0.4)
ax_cum.set_title('Cumulative VRP Captured — OOS 2022–2026')
ax_cum.set_ylabel('Cumulative VRP')
ax_cum.legend(facecolor='#222222', labelcolor=WHITE, fontsize=9)
ax_cum.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

strategies  = ['Always-in', 'Naive binary', f'ARMA timed']
hit_rates   = [stats_always['hit_rate'], stats_naive['hit_rate'], stats_arma['hit_rate']]
bar_colors  = ['#60a5fa', '#a78bfa', '#4ade80']
bars = ax_bar.bar(strategies, hit_rates, color=bar_colors, alpha=0.85, width=0.5)
ax_bar.set_ylim(0.7, 1.0)
ax_bar.set_title('Hit Rate (OOS)')
ax_bar.set_ylabel('Fraction of days VRP > 0')
for bar, val in zip(bars, hit_rates):
    ax_bar.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                f'{val:.1%}', ha='center', va='bottom', color=WHITE, fontsize=9)
ax_bar.tick_params(axis='x', colors=WHITE, labelsize=8)

plot_vrp_kde(ax_d1, actual_next[always_in].values,
             f'Always-in ({stats_always["days_in"]} days)')
plot_vrp_kde(ax_d2, actual_next[naive_in].values,
             f'Naive binary ({stats_naive["days_in"]} days)')
plot_vrp_kde(ax_d3, actual_next[arma_in].values,
             f'ARMA-timed ({stats_arma["days_in"]} days)')

fig2.suptitle('Figure 2 — Strategy Comparison: Naive Binary Dominates Out-of-Sample',
              color=WHITE, fontsize=11, y=1.01)
img2 = fig_to_b64(fig2)


# ── SLIDE figure (large single panel) ────────────────────────────────────────

fig_slide, ax_s = plt.subplots(figsize=(14, 6))
fig_slide.patch.set_facecolor(DARK_BG)
dark_ax(ax_s)
ax_s.plot(always_cum.index, always_cum.values, color='#60a5fa', lw=2,
          label=f'Always-in  |  hit {stats_always["hit_rate"]:.1%}  |  CVaR 95% {stats_always["cvar"]:.3f}',
          alpha=0.75)
ax_s.plot(naive_cum.index,  naive_cum.values,  color='#a78bfa', lw=2.5,
          label=f'Naive binary (VRP > 0 today)  |  hit {stats_naive["hit_rate"]:.1%}  |  CVaR 95% {stats_naive["cvar"]:.3f}')
ax_s.plot(arma_cum.index,   arma_cum.values,   color='#4ade80', lw=2,
          label=f'ARMA({p_best},{q_best}) timed  |  hit {stats_arma["hit_rate"]:.1%}  |  CVaR 95% {stats_arma["cvar"]:.3f}',
          alpha=0.75)
ax_s.axhline(0, color=WHITE, lw=0.6, linestyle='--', alpha=0.3)
ax_s.set_title('VRP Signal — Cumulative Performance OOS (2022–2026)', fontsize=14)
ax_s.set_ylabel('Cumulative VRP Captured', fontsize=11)
ax_s.legend(facecolor='#222222', labelcolor=WHITE, fontsize=10)
ax_s.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
fig_slide.tight_layout()
img_slide = fig_to_b64(fig_slide)


# ── HTML REPORT ───────────────────────────────────────────────────────────────

report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VRP-ARMA Signal — Summary Analysis Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #ffffff;
    color: #1a1a1a;
    font-size: 10.5pt;
    line-height: 1.65;
  }}
  .page {{
    max-width: 800px;
    margin: 0 auto;
    padding: 60px 70px;
  }}
  h1 {{
    font-size: 20pt;
    font-weight: 600;
    letter-spacing: -0.02em;
    border-bottom: 2px solid #111;
    padding-bottom: 10px;
    margin-bottom: 6px;
  }}
  .subtitle {{
    color: #555;
    font-size: 9.5pt;
    margin-bottom: 36px;
  }}
  h2 {{
    font-size: 12pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #111;
    margin-top: 32px;
    margin-bottom: 10px;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 4px;
  }}
  p {{ margin-bottom: 10px; }}
  ul {{ margin: 8px 0 10px 20px; }}
  li {{ margin-bottom: 4px; }}
  .figure {{
    margin: 20px 0 8px;
    text-align: center;
  }}
  .figure img {{
    width: 100%;
    border-radius: 6px;
  }}
  .caption {{
    font-size: 8.5pt;
    color: #666;
    text-align: center;
    margin-bottom: 18px;
    font-style: italic;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 9.5pt;
  }}
  th {{
    background: #f4f4f4;
    font-weight: 600;
    padding: 7px 12px;
    text-align: left;
    border-bottom: 2px solid #ddd;
  }}
  td {{
    padding: 6px 12px;
    border-bottom: 1px solid #eee;
  }}
  tr.highlight td {{
    background: #f0f7ff;
    font-weight: 500;
  }}
  .callout {{
    background: #f8f8f8;
    border-left: 3px solid #111;
    padding: 10px 16px;
    margin: 14px 0;
    font-size: 9.5pt;
  }}
  .superseded {{
    background: #fff4f4;
    border: 1px solid #e5b4b4;
    border-left: 4px solid #c0392b;
    padding: 14px 18px;
    margin-bottom: 28px;
    font-size: 9pt;
    line-height: 1.55;
  }}
  .superseded strong {{ color: #a3271c; }}
  @media print {{
    body {{ font-size: 10pt; }}
    .page {{ padding: 40px 50px; }}
  }}
</style>
</head>
<body>
<div class="page">

  <h1>Variance Risk Premium Signal</h1>
  <div class="subtitle">Summary Analysis Report &nbsp;·&nbsp; Sentinel Research &nbsp;·&nbsp; April 2026</div>

  <div class="superseded">
    <strong>⚠️ Superseded — the conclusions in this report are known to be invalid (2026-08-04).</strong><br>
    Adversarial audits found a walk-forward off-by-one that scored the ARMA model as a 2-step forecast
    against naive persistence's 1-step. Re-executed with the alignment corrected, ARMA RMSE is 0.0318 vs
    naive 0.0327 (Diebold–Mariano p=0.30): <strong>the headline finding that naive persistence beats ARMA
    is an artifact of that bug</strong>, and the corrected result is that the two are statistically
    indistinguishable. Separately, VRP here subtracts a 1-day-ahead GARCH vol from 30-calendar-day implied
    vol, so the level statistics conflate risk premium with a term-structure artifact; and "cumulative VRP
    captured" sums spread levels, which are not the P&amp;L of any instrument. Superseded by the v2 study
    (<em>research/vrp_tail_v2.ipynb</em>, spec <em>docs/specs/vrp-tail-v2.md</em>). Retained as a record of
    the first attempt.
  </div>

  <h2>1. Dataset & Source</h2>
  <p>
    Daily closing prices for <strong>SPY</strong> (S&amp;P 500 ETF) and <strong>^VIX</strong>
    (CBOE Volatility Index) were downloaded from Yahoo Finance via yfinance, covering
    <strong>January 2016 – January 2026</strong> (2,515 trading days).
    Data was pinned to a local CSV for reproducibility.
  </p>
  <ul>
    <li><strong>Train period:</strong> 2016–2021 (1,490 days). GARCH and ARMA parameters estimated here.</li>
    <li><strong>Test period (OOS):</strong> 2022–2026 (1,003 days). All strategy evaluation done here.</li>
    <li>The 2022 cutoff marks a natural structural break: the Fed rate-hike cycle began and the volatility regime shifted, making it a meaningfully harder OOS period.</li>
  </ul>

  <h2>2. Overview of Methods</h2>
  <p>
    The goal was to build a <strong>forward-looking entry signal</strong> for selling variance risk premium,
    the systematic spread between implied volatility (VIX) and realized volatility. The approach used a
    two-model pipeline:
  </p>
  <ul>
    <li>
      <strong>GARCH(1,1) with Student-t innovations.</strong> Fit on SPY log returns to estimate daily
      conditional volatility. Stock returns have fat tails, meaning extreme moves happen more often than
      a normal distribution predicts. Student-t was used to account for this and confirmed by model
      scoring. GARCH was preferred over a rolling window because rolling windows inflate apparent
      autocorrelation and would distort model selection downstream.
    </li>
    <li>
      <strong>VRP construction.</strong> VRP = VIX (decimal) minus GARCH conditional vol. Both series
      are mean-reverting, so their difference is stationary, confirmed statistically. Stationarity is a
      core requirement for the forecasting model used in the next step.
    </li>
    <li>
      <strong>ARMA(p,q) grid search.</strong> A family of time-series forecasting models tested over all
      combinations up to order 3. The best model was selected by AIC, a scoring criterion that balances
      fit quality against model complexity. Forecasts were generated walk-forward with parameters fixed
      at train values, with no lookahead bias.
    </li>
    <li>
      <strong>Three strategies backtested over OOS:</strong> always-in, naive binary
      (in when today's VRP &gt; 0), and ARMA-timed (in when tomorrow's forecast &gt; 0).
    </li>
  </ul>

  <h2>3. Key Findings</h2>

  <div class="figure">
    <img src="data:image/png;base64,{img1}" alt="VRP signal and distribution">
  </div>
  <p class="caption">
    Figure 1 — VRP time series (2016–2026). Green shading: implied vol overpriced (signal present).
    Red shading: implied vol underpriced. Blue dashed line marks the train/OOS boundary.
    Right panel: full-period VRP distribution. Dotted lines mark the CVaR 95% tails,
    the average of the worst and best 5% of days.
  </p>

  <p>
    Implied volatility (VIX) systematically overprices realized volatility. VRP is positive on
    <strong>{hit:.1%} of days</strong> with a mean of approximately 3 vol points. This structural
    overpricing held across calm, elevated, and stress VIX regimes, including through the 2022
    rate-hike cycle and the early-2025 vol spike visible in Figure 1.
  </p>
  <p>
    The loss tail is fat, however. The worst 5% of days average a VRP of {cl:.3f} (CVaR 95%),
    representing large negative spikes where implied vol briefly underprices realized vol. An always-in
    position is fully exposed to these events. The goal of the signal is to step out on days when VRP
    is likely to turn negative, shaving the loss tail without giving up the structural edge on the
    remaining days.
  </p>
  <p>
    VRP is also strongly autocorrelated: positive VRP today is a reliable predictor of positive VRP
    tomorrow. This persistence follows from volatility clustering. Large moves cluster in time, so both
    implied and realized vol are sticky, and their spread inherits that stickiness. The central question
    was whether a forecasting model could exploit this persistence better than a simple rule.
  </p>

  <div class="figure">
    <img src="data:image/png;base64,{img2}" alt="Strategy comparison">
  </div>
  <p class="caption">
    Figure 2 — OOS strategy comparison. Top left: cumulative VRP captured. Top right: hit rate per strategy.
    Bottom: VRP distribution for each strategy's active days. Dotted lines mark CVaR 95% loss and win tails.
  </p>

  <p><strong>The naive binary rule outperformed ARMA on every metric:</strong></p>
  <table>
    <tr>
      <th>Strategy</th>
      <th>Days in (OOS)</th>
      <th>Hit Rate</th>
      <th>Mean VRP</th>
      <th>CVaR 95% (loss)</th>
    </tr>
    <tr>
      <td>Always-in</td>
      <td>{stats_always['days_in']}</td>
      <td>{stats_always['hit_rate']:.1%}</td>
      <td>{stats_always['mean_vrp']:.4f}</td>
      <td>{stats_always['cvar']:.3f}</td>
    </tr>
    <tr class="highlight">
      <td><strong>Naive binary</strong></td>
      <td><strong>{stats_naive['days_in']}</strong></td>
      <td><strong>{stats_naive['hit_rate']:.1%}</strong></td>
      <td><strong>{stats_naive['mean_vrp']:.4f}</strong></td>
      <td><strong>{stats_naive['cvar']:.3f}</strong></td>
    </tr>
    <tr>
      <td>ARMA({p_best},{q_best}) timed</td>
      <td>{stats_arma['days_in']}</td>
      <td>{stats_arma['hit_rate']:.1%}</td>
      <td>{stats_arma['mean_vrp']:.4f}</td>
      <td>{stats_arma['cvar']:.3f}</td>
    </tr>
  </table>

  <div class="callout">
    Naive binary achieved a <strong>{stats_naive['hit_rate']:.1%} hit rate</strong> while taking
    <strong>{int(stats_always['days_in'] - stats_naive['days_in'])} fewer days at risk</strong> than
    always-in, cutting the worst-case tail loss from {stats_always['cvar']:.3f} to {stats_naive['cvar']:.3f}.
    ARMA-timed took on {int(stats_arma['days_in'] - stats_naive['days_in'])} more days at risk with a lower
    hit rate. Its claimed lead-time advantage at VRP zero-crossings did not materialize out-of-sample.
  </div>

  <p>
    This is a common pattern in financial forecasting. Models that fit training dynamics well frequently
    lose to simpler rules when the market regime shifts. ARMA(3,3) fit the training period cleanly but
    extrapolated persistence into vol spikes out-of-sample, generating false positives that naive binary
    correctly avoided. On pure forecast accuracy, ARMA also came up short: RMSE {rmse_arma:.4f} versus
    {rmse_naive:.4f} for naive persistence. The forecast edge simply was not there.
  </p>

  <h2>4. Reflection</h2>
  <p>
    The VRP edge is real and structurally grounded. The core mechanism, vol clustering and VIX stickiness,
    held through a rate-hike cycle and multiple vol spikes. The actionable signal is the naive binary rule:
    no model risk, straightforward to implement, and it correctly avoids the false positives that hurt ARMA.
  </p>
  <p>
    The main limitation is tail risk concentration. Both CVaR numbers are dominated by two discrete events
    in late 2022 and early 2025. No daily entry signal can anticipate sudden regime transitions of that
    kind. Position sizing and risk limits are the right tool there, not a more sophisticated entry filter.
  </p>
  <p>
    A natural next step is combining this signal with an HMM regime filter, already explored in a separate
    notebook, to reduce exposure during stress regimes. Longer term, the naive binary signal is a candidate
    for integration into the Sentinel pipeline for live monitoring.
  </p>

</div>
</body>
</html>"""


# ── HTML SLIDE ─────────────────────────────────────────────────────────────────

slide_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {DARK_BG};
    width: 1280px;
    height: 720px;
    overflow: hidden;
    font-family: 'Inter', -apple-system, sans-serif;
    color: white;
    display: flex;
    flex-direction: column;
    padding: 36px 48px 28px;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
  }}
  .title {{ font-size: 22px; font-weight: 600; letter-spacing: -0.01em; }}
  .subtitle {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .tag {{
    font-size: 11px;
    background: #222;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px 10px;
    color: #aaa;
    white-space: nowrap;
    margin-top: 4px;
  }}
  .chart {{ flex: 1; text-align: center; }}
  .chart img {{ height: 100%; max-height: 460px; border-radius: 6px; }}
  .footer {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 14px;
  }}
  .stats {{
    display: flex;
    gap: 28px;
  }}
  .stat-block {{ text-align: center; }}
  .stat-value {{ font-size: 20px; font-weight: 600; }}
  .stat-label {{ font-size: 10px; color: #888; margin-top: 2px; }}
  .green {{ color: #4ade80; }}
  .blue  {{ color: #a78bfa; }}
  .finding {{
    font-size: 11.5px;
    color: #aaa;
    max-width: 380px;
    line-height: 1.5;
    text-align: right;
  }}
  .finding strong {{ color: #e5e5e5; }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">Variance Risk Premium Signal</div>
      <div class="subtitle">Naive Binary Rule Beats ARMA Out-of-Sample &nbsp;·&nbsp; SPY/VIX 2022–2026</div>
    </div>
    <div class="tag" style="border-color:#7f2a22; background:#2a1513; color:#e08b80;">
      ⚠️ SUPERSEDED — see vrp_tail_v2
    </div>
  </div>

  <div class="chart">
    <img src="data:image/png;base64,{img_slide}" alt="Cumulative VRP">
  </div>

  <div class="footer">
    <div class="stats">
      <div class="stat-block">
        <div class="stat-value blue">{stats_naive['hit_rate']:.1%}</div>
        <div class="stat-label">Hit Rate<br>Naive Binary</div>
      </div>
      <div class="stat-block">
        <div class="stat-value green">{int(stats_always['days_in'] - stats_naive['days_in'])}</div>
        <div class="stat-label">Fewer Days<br>at Risk</div>
      </div>
      <div class="stat-block">
        <div class="stat-value" style="color:#f87171;">{stats_naive['cvar']:.3f}</div>
        <div class="stat-label">CVaR 95%<br>vs {stats_always['cvar']:.3f} always-in</div>
      </div>
      <div class="stat-block">
        <div class="stat-value" style="color:#fde047;">{hit:.0%}</div>
        <div class="stat-label">Days VRP &gt; 0<br>2016–2026</div>
      </div>
    </div>
    <div class="finding">
      VIX systematically overprices realized vol. <strong>Simple persistence beats ARMA</strong>
      on hit rate and tail risk — ARMA's lead-time advantage at zero-crossings did not materialize OOS.
    </div>
  </div>
</body>
</html>"""


# ── write files ───────────────────────────────────────────────────────────────

report_path = os.path.join(DESKTOP, 'VRP-ARMA_Report.html')
slide_path  = os.path.join(DESKTOP, 'VRP-ARMA_Slide.html')

with open(report_path, 'w') as f:
    f.write(report_html)
with open(slide_path, 'w') as f:
    f.write(slide_html)

print(f'\nSaved:')
print(f'  Report: {report_path}')
print(f'  Slide:  {slide_path}')
print('\nOpen each in Chrome and use Cmd+P → Save as PDF to export.')
