import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import SimulationRequest, SimulationResponse
from ..runtime.simulate import run_simulation

logging.basicConfig(level=logging.WARNING)                                                                                                                                             
logging.getLogger('backend').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

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

@app.post('/simulate', response_model=SimulationResponse)
def simulate(req: SimulationRequest) -> SimulationResponse:
    try:
        return run_simulation(req)
    except ValueError as e:
        logger.warning(e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail='Internal engine error')
