import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import diskcache

from finn.config import CACHE_DIR, SNAPSHOT_DIR

logger = logging.getLogger(__name__)

_cache = diskcache.Cache(str(CACHE_DIR))
_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

# AI results are slow and use quota, so they are also kept as files in the repo.
# A restart or redeploy reloads them instead of asking the model again.
SNAPSHOT_PREFIXES = ("analysis:", "bio:")


def _snapshot_path(key: str):
    kind = key.split(":", 1)[0]
    return SNAPSHOT_DIR / kind / f"{hashlib.sha1(key.encode()).hexdigest()[:20]}.json"


def snapshot_load(key: str) -> Optional[Any]:
    if not key.startswith(SNAPSHOT_PREFIXES):
        return None
    try:
        data = json.loads(_snapshot_path(key).read_text(encoding="utf-8"))
        return data["value"] if data.get("key") == key else None
    except (OSError, ValueError, KeyError):
        return None


def snapshot_save(key: str, value: Any) -> None:
    if not key.startswith(SNAPSHOT_PREFIXES):
        return
    path = _snapshot_path(key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = {"key": key, "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "value": value}
        path.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as e:
        logger.warning(f"Could not save snapshot for {key}: {e}")


def snapshot_forget(key: str) -> None:
    try:
        _snapshot_path(key).unlink()
    except OSError:
        pass


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
            value = snapshot_load(key)
            if value is None:
                value = compute()
                if value is not None:
                    snapshot_save(key, value)
            if value is not None:
                _cache.set(key, value, expire=ttl_seconds)
        return value


def cache_get(key: str) -> Any:
    value = _cache.get(key)
    return value if value is not None else snapshot_load(key)


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    _cache.set(key, value, expire=ttl_seconds)
