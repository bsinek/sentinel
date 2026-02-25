from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import SimulationRequest, SimulationResponse, MetricsResult
from engine.data import fetch_prices
from engine.estimation import estimate_params
from engine.gbm import simulate_gbm
from engine.portfolio import aggregate_portfolio
from engine.risk import summary

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
        prices = fetch_prices(req.tickers, str(req.start), str(req.end), req.interval)
        S0, mu, cov = estimate_params(prices)
        asset_paths = simulate_gbm(S0, mu, cov, req.n_steps, req.n_sims)
        portfolio_paths = aggregate_portfolio(asset_paths, req.weights)

        response = SimulationResponse()

        if 'asset_paths' in req.include:
            response.asset_paths = asset_paths.tolist()
        if 'portfolio_paths' in req.include:
            response.portfolio_paths = portfolio_paths.tolist()
        if 'metrics' in req.include:
            metrics = summary(portfolio_paths, interval_to_dt(req.interval), req.alpha, req.risk_free_rate)
            response.metrics = MetricsResult(**metrics)
        
        return response

    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Internal engine error')
