import time
import logging
from datetime import date

from . import cache
from ..api.schemas import SimulationRequest, SimulationResponse, MetricsResult, ProjectionResult
from ..engine.data import fetch_prices
from ..engine.estimation import estimate_params
from ..engine.gbm import simulate_gbm
from ..engine.portfolio import aggregate_portfolio
from ..engine.risk import summary
from ..engine.projection import prepare_projection

logger = logging.getLogger(__name__)


def get_price_key(tickers: list[str], start: date, end: date) -> str:
    sorted_tickers = ','.join(sorted(tickers))
    return f'prices:{sorted_tickers}:{start}:{end}'


def interval_to_dt(interval: str) -> float:
    mapping = {
        '1d': 1/252,
        '1wk': 1/52,
        '1mo': 1/12,
    }
    return mapping[interval]


def run_simulation(req: SimulationRequest):
    t0 = time.perf_counter()

    price_key = get_price_key(req.tickers, req.start, req.end)
    prices = cache.get(price_key)
    if prices is None:
        t_fetch = time.perf_counter()
        prices = fetch_prices(req.tickers, str(req.start), str(req.end))
        logger.debug(f'FETCH: {time.perf_counter() - t_fetch:.3f}s')
        cache.set(price_key, prices)

    S0, mu, cov = estimate_params(prices)
    dt = interval_to_dt(req.interval)

    t_sim = time.perf_counter()
    asset_paths = simulate_gbm(S0, mu, cov, dt, req.n_steps, req.n_sims)
    logger.debug(f'SIMULATE: {time.perf_counter() - t_sim:.3f}s')

    t_port = time.perf_counter()
    portfolio_paths = aggregate_portfolio(asset_paths, req.weights)
    logger.debug(f'AGGREGATE: {time.perf_counter() - t_port:.3f}s')

    response = SimulationResponse()

    if 'metrics' in req.include:
        t_metrics = time.perf_counter()
        response.metrics = MetricsResult(**summary(portfolio_paths, dt, req.alpha, req.risk_free_rate))
        logger.debug(f'METRICS: {time.perf_counter() - t_metrics:.3f}s')
    if 'projection' in req.include:
        t_proj = time.perf_counter()
        response.projection = ProjectionResult(**prepare_projection(portfolio_paths, req.alpha, req.n_samples))
        logger.debug(f'PROJECTION: {time.perf_counter() - t_proj:.3f}s')

    logger.debug(f'TOTAL: {time.perf_counter() - t0:.3f}s')
    return response
