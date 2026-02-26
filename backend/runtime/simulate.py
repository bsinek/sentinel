from ..api.schemas import SimulationRequest, SimulationResponse, MetricsResult, ProjectionResult
from ..engine.data import fetch_prices
from ..engine.estimation import estimate_params
from ..engine.gbm import simulate_gbm
from ..engine.portfolio import aggregate_portfolio
from ..engine.risk import summary
from ..engine.projection import prepare_projection

def interval_to_dt(interval: str) -> float:
    mapping = {
        '1d': 1/252,
        '1wk': 1/52,
        '1mo': 1/12,
    }
    return mapping[interval]

def run_simulation(req: SimulationRequest):
    prices = fetch_prices(req.tickers, str(req.start), str(req.end))
    S0, mu, cov = estimate_params(prices)
    dt = interval_to_dt(req.interval)
    asset_paths = simulate_gbm(S0, mu, cov, dt, req.n_steps, req.n_sims)
    portfolio_paths = aggregate_portfolio(asset_paths, req.weights)
    
    response = SimulationResponse()

    if 'metrics' in req.include:
        response.metrics = MetricsResult(**summary(portfolio_paths, dt, req.alpha, req.risk_free_rate))
    if 'projection' in req.include:
        response.projection = ProjectionResult(**prepare_projection(portfolio_paths, req.alpha, req.n_samples))

    return response
