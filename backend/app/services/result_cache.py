"""Short-lived cache for computed analysis results (map rasters, time series).

Keys are SHA-256 digests of every input that affects a result (site, index,
dates, cloud threshold, ROI source/version/geometry hash and a fingerprint of
the processing method), so different analyses can never share an entry.
Values are the exact bytes produced by Sentinel Hub processing; nothing is
synthesised. Only public analysis results are cached, never credentials or
tokens.

Backend (RESULT_CACHE_BACKEND):
- "auto"   Redis at REDIS_URL if it answers, otherwise an in-process cache;
- "redis"  Redis only (falls back to no caching if unreachable);
- "memory" in-process LRU, bounded by RESULT_CACHE_MAX_MEMORY_MB;
- "off"    no caching.
The in-process cache is per worker process and is lost on restart.
"""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)
_PREFIX = "wq-result:"


def cache_key(kind: str, parts: dict[str, Any]) -> str:
    payload = json.dumps({"kind": kind, **parts}, sort_keys=True, default=str)
    return _PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResultCache(Protocol):
    backend: str

    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes, ttl_seconds: int) -> None: ...
    def clear(self) -> None: ...


class NullCache:
    backend = "off"

    def get(self, key: str) -> bytes | None:
        return None

    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        return None

    def clear(self) -> None:
        return None


class MemoryCache:
    """Thread-safe LRU with per-entry expiry and a total size bound."""

    backend = "memory"

    def __init__(self, max_bytes: int, clock: Any = time.monotonic) -> None:
        self._max_bytes = max_bytes
        self._clock = clock
        self._items: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self._size = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires, value = item
            if self._clock() >= expires:
                self._drop(key)
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        if len(value) > self._max_bytes:
            return  # larger than the whole cache: do not evict everything for it
        with self._lock:
            if key in self._items:
                self._drop(key)
            self._items[key] = (self._clock() + ttl_seconds, value)
            self._size += len(value)
            while self._size > self._max_bytes:
                oldest = next(iter(self._items))
                self._drop(oldest)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._size = 0

    def _drop(self, key: str) -> None:
        _, value = self._items.pop(key)
        self._size -= len(value)


class RedisCache:
    backend = "redis"

    def __init__(self, client: Any) -> None:
        self._client = client

    def get(self, key: str) -> bytes | None:
        try:
            value = self._client.get(key)
        except Exception:  # noqa: BLE001 - a cache failure must never break an analysis
            logger.warning("Result cache read failed; continuing without cache.")
            return None
        return value if isinstance(value, bytes) else None

    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        try:
            self._client.set(key, value, ex=ttl_seconds)
        except Exception:  # noqa: BLE001
            logger.warning("Result cache write failed; result not cached.")

    def clear(self) -> None:
        try:
            for key in self._client.scan_iter(match=_PREFIX + "*"):
                self._client.delete(key)
        except Exception:  # noqa: BLE001
            logger.warning("Result cache clear failed.")


def _redis_or_none() -> RedisCache | None:
    try:
        import redis

        client = redis.Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=2
        )
        client.ping()
        return RedisCache(client)
    except Exception:  # noqa: BLE001
        return None


@lru_cache
def get_result_cache() -> ResultCache:
    mode = settings.RESULT_CACHE_BACKEND
    memory = MemoryCache(settings.RESULT_CACHE_MAX_MEMORY_MB * 1024 * 1024)
    if mode == "off":
        return NullCache()
    if mode == "memory":
        return memory
    redis_cache = _redis_or_none()
    if redis_cache is not None:
        logger.info("Result cache: Redis.")
        return redis_cache
    if mode == "redis":
        logger.warning("Result cache: Redis unreachable; caching disabled.")
        return NullCache()
    logger.info("Result cache: Redis unreachable; using the in-process cache.")
    return memory
