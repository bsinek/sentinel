from backend.celery import app
from backend.api.schemas import SimulationRequest
from backend.pipelines.simulate import run_simulation


@app.task(name='simulate')
def run_simulation_task(params: dict) -> dict:
    req = SimulationRequest(**params)
    result = run_simulation(req)
    return result.model_dump()
