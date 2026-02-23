from pydantic import BaseModel
from typing import Literal
from datetime import date

class SimulationRequest(BaseModel):
    tickers: list[str]
    start: date
    end: date
    interval: Literal['1d', '1wk', '1mo'] = '1d'
    n_steps: int = 252
    n_sims: int = 1000
    alpha: float = 0.95
    risk_free_rate: float = 0.0
    weights: list[float] | None = None
    include: list[Literal['asset_paths', 'portfolio_paths', 'metrics']] = ['metrics']

class MetricsResult(BaseModel):
    mean_return: float
    median_return: float
    median_cagr: float
    volatility: float
    sharpe: float
    var: float
    cvar: float
    mean_mdd: float
    worst_mdd: float
    prob_loss: float

class SimulationResponse(BaseModel):
    asset_paths: list | None = None
    portfolio_paths: list | None = None
    metrics: MetricsResult | None = None
