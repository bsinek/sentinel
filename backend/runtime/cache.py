import redis
import pickle
from typing import Any

DEFAULT_TTL = 86400     # 1 day

_redis = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1, socket_timeout=1)


def get(key: str) -> Any | None:
    try:
        raw = _redis.get(key)
        if raw is None:
            print(f'CACHE MISS: {key}')
            return None
        print(f'CACHE HIT: {key}')
        return pickle.loads(raw)
    except Exception as e:
        print(f'CACHE ERROR: {e}')
        return None


def set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    try:
        serialized_value = pickle.dumps(value)
        _redis.set(key, serialized_value, ex=ttl)

        size_kb = len(serialized_value)
        if size_kb > 1024:
            print(f'CACHE SET: {key} ({size_kb/1024:.2f} MB)')
        else:
            print(f'CACHE SET: {key} ({size_kb:.2f} KB)')
    except Exception as e:
        print(f'CACHE ERROR: {e}')
        return
