"""TTL-based cache for repeated-expensive deterministic ops.

The new dashboards rebuild model panels on every page load — the
default panels are synthesized from deterministic seeds and don't
change request-to-request. Caching them eliminates wasted CPU
on every refresh.

functools.lru_cache covers immutable-arg cases but doesn't expire,
so a stale-data risk creeps in for cases where the underlying
state can change (DB rows, ingest tables). This module ships a
lightweight TTL cache with explicit invalidation.

Public API::

    from rcm_mc.infra.cache import ttl_cache

    @ttl_cache(seconds=300)
    def expensive_op(arg1, arg2):
        ...

    expensive_op.cache_clear()  # explicit invalidation
    expensive_op.cache_info()   # hit/miss stats

Thread-safe. Cache key built from positional + keyword args
(must be hashable). Returns identical-by-reference values on
cache hits, so callers must not mutate the result in place.
"""
from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple


@dataclass
class CacheInfo:
    """Mirrors functools.lru_cache.cache_info shape so existing
    monitoring scripts continue to work."""
    hits: int
    misses: int
    currsize: int
    maxsize: int = 256


def ttl_cache(
    *,
    seconds: float,
    maxsize: int = 256,
):
    """Decorator: cache a function's return for ``seconds``.

    Args:
      seconds: TTL. Must be positive.
      maxsize: max distinct keys retained. Oldest evicted on overflow.

    Returns: decorator that adds ``cache_clear()`` and
    ``cache_info()`` to the wrapped function.
    """
    if seconds <= 0:
        raise ValueError(
            "ttl_cache seconds must be > 0")

    def decorator(fn: Callable[..., Any]
                  ) -> Callable[..., Any]:
        cache: Dict[Tuple, Tuple[float, Any]] = {}
        lock = threading.RLock()
        stats = {"hits": 0, "misses": 0}

        def _key(args: Tuple,
                 kwargs: Dict[str, Any]) -> Tuple:
            if kwargs:
                return args + tuple(
                    sorted(kwargs.items()))
            return args

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _key(args, kwargs)
            now = time.monotonic()
            with lock:
                hit = cache.get(key)
                if hit is not None:
                    expires_at, value = hit
                    if now < expires_at:
                        stats["hits"] += 1
                        return value
                    # Expired — drop and recompute below
                    del cache[key]
                stats["misses"] += 1

            value = fn(*args, **kwargs)

            with lock:
                # Evict oldest if at capacity
                if len(cache) >= maxsize:
                    oldest = min(
                        cache.items(),
                        key=lambda kv: kv[1][0])[0]
                    cache.pop(oldest, None)
                cache[key] = (now + seconds, value)
            return value

        def cache_clear() -> None:
            with lock:
                cache.clear()
                stats["hits"] = 0
                stats["misses"] = 0

        def cache_info() -> CacheInfo:
            with lock:
                return CacheInfo(
                    hits=stats["hits"],
                    misses=stats["misses"],
                    currsize=len(cache),
                    maxsize=maxsize)

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        wrapper.cache_info = cache_info  # type: ignore[attr-defined]
        return wrapper

    return decorator
