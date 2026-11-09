import logging
import threading
from typing import Any, Callable, Dict

import diskcache

from finn.config import CACHE_DIR

logger = logging.getLogger(__name__)

_cache = diskcache.Cache(str(CACHE_DIR))
_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def cached(key: str, ttl_seconds: int, compute: Callable[[], Any]) -> Any:
    """Returns the cached value for key, computing it once even under concurrent requests."""
    value = _cache.get(key)
    if value is not None:
        return value
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        value = _cache.get(key)
        if value is None:
            value = compute()
            if value is not None:
                _cache.set(key, value, expire=ttl_seconds)
        return value


def cache_get(key: str) -> Any:
    return _cache.get(key)


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    _cache.set(key, value, expire=ttl_seconds)
