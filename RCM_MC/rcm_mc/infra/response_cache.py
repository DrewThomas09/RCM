"""Simple in-memory response cache for expensive JSON endpoints.

Keyed on (path, query_string). TTL-based expiry. Thread-safe.
Used for portfolio MC, attribution, heatmap — routes that read
across all deals and take 100ms+ on large portfolios.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class ResponseCache:
    """TTL-based in-process cache for JSON response bodies."""

    def __init__(self, default_ttl: float = 60.0, max_entries: int = 100):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = float(default_ttl)
        self._max_entries = int(max_entries)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, *, ttl: Optional[float] = None) -> None:
        with self._lock:
            # Evict oldest if at capacity.
            if len(self._store) >= self._max_entries:
                oldest_key = min(
                    self._store, key=lambda k: self._store[k][1],
                )
                del self._store[oldest_key]
            self._store[key] = (
                value,
                time.monotonic() + (ttl or self._default_ttl),
            )

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)
