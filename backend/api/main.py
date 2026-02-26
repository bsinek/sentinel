from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import SimulationRequest, SimulationResponse, MetricsResult, ProjectionResult
from ..engine.data import fetch_prices
from ..engine.estimation import estimate_params
from ..engine.gbm import simulate_gbm
from ..engine.portfolio import aggregate_portfolio
from ..engine.risk import summary
from ..engine.projection import prepare_projection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/health')
def health():
    return {'status' : 'ok'}

def interval_to_dt(interval: str) -> float:
    mapping = {
        '1d': 1/252,
        '1wk': 1/52,
        '1mo': 1/12,
    }
    return mapping[interval]

@app.post('/simulate', response_model=SimulationResponse)
def simulate(req: SimulationRequest):
    try:
        prices = fetch_prices(req.tickers, str(req.start), str(req.end))
        S0, mu, cov = estimate_params(prices)
        asset_paths = simulate_gbm(S0, mu, cov, interval_to_dt(req.interval), req.n_steps, req.n_sims)
        portfolio_paths = aggregate_portfolio(asset_paths, req.weights)

        response = SimulationResponse()

        if 'metrics' in req.include:
            response.metrics = MetricsResult(**summary(portfolio_paths, interval_to_dt(req.interval), req.alpha, req.risk_free_rate))
        if 'projection' in req.include:
            response.projection = ProjectionResult(**prepare_projection(portfolio_paths, req.alpha, req.n_samples))
        
        return response

    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Internal engine error')
