import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import SimulationRequest, SimulationResult, JobSubmitResponse, JobStatusResponse
from ..celery import app as celery_app
from ..tasks.simulate import run_simulation_task

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

_STATE_MAP = {
    'PENDING': 'pending',
    'STARTED': 'running',
    'SUCCESS': 'completed',
    'FAILURE': 'failed',
}


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/jobs', response_model=JobSubmitResponse)
def submit_job(req: SimulationRequest) -> JobSubmitResponse:
    task = run_simulation_task.delay(req.model_dump(mode='json'))
    return JobSubmitResponse(job_id=task.id)


@app.get('/jobs/{job_id}', response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    result = celery_app.AsyncResult(job_id)
    status = _STATE_MAP.get(result.state, 'pending')

    if result.state == 'SUCCESS':
        return JobStatusResponse(
            job_id=job_id,
            status='completed',
            result=SimulationResult(**result.result),
        )
    if result.state == 'FAILURE':
        return JobStatusResponse(
            job_id=job_id,
            status='failed',
            error=str(result.result),
        )

    return JobStatusResponse(job_id=job_id, status=status)
