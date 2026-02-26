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
    n_samples: int = 50
    include: list[Literal['metrics', 'projection']] = ['metrics', 'projection']


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


class ProjectionResult(BaseModel):
    confidence_bands: dict[str, list[float]]
    sample_paths: list[list[float]]


class SimulationResponse(BaseModel):
    metrics: MetricsResult | None = None
    projection: ProjectionResult | None = None
