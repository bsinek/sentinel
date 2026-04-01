import os
from celery import Celery

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

app = Celery('sentinel')

app.conf.update(
    broker_url=f'{REDIS_URL}/0',       # task queue
    result_backend=f'{REDIS_URL}/1',   # task results
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,           # exposes STARTED state so we can show "running"
    task_acks_late=True,               # don't remove task from queue until it finishes
    worker_prefetch_multiplier=1,      # one task at a time per worker process
    worker_concurrency=2,              # max 2 simultaneous simulations; leaves cores free for local dev
    worker_max_tasks_per_child=50,     # restart worker process after 50 tasks; prevents numpy/pandas memory accumulation
    imports=['backend.tasks.simulate'],
)
