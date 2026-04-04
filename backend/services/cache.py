import os
import logging
import pickle
import redis
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TTL = 86400     # 1 day

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

_redis = redis.Redis.from_url(url=f'{REDIS_URL}/2', socket_connect_timeout=1, socket_timeout=0.1, retry_on_timeout=True)


def get(key: str) -> Any | None:
    try:
        raw = _redis.get(key)
        if raw is None:
            logger.debug(f'CACHE MISS: {key}')
            return None
        logger.debug(f'CACHE HIT: {key}')
        return pickle.loads(raw)
    except Exception as e:
        logger.warning(f'CACHE ERROR: {e}')
        return None


def set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    try:
        serialized_value = pickle.dumps(value)
        _redis.set(key, serialized_value, ex=ttl)

        size_kb = len(serialized_value)
        if size_kb > 1024:
            logger.debug(f'CACHE SET: {key} ({size_kb/1024:.2f} MB)')
        else:
            logger.debug(f'CACHE SET: {key} ({size_kb:.2f} KB)')
    except Exception as e:
        logger.warning(f'CACHE ERROR: {e}')
