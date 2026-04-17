"""Small in-memory sliding-window rate limiter.

Used by endpoints we don't want partners hammering — principally
``/api/data/refresh/<source>`` where each call may spin up a real
CMS download. Fails open on process restart (limits are in-memory) —
we accept that because the worst case is one extra refresh, not a
security breach.

Simple because nothing here merits a Redis dep.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Tuple


class RateLimiter:
    """Per-key sliding window. Thread-safe for the ThreadingHTTPServer
    concurrency model.
    """

    def __init__(self, *, max_hits: int, window_secs: int) -> None:
        self.max_hits = int(max_hits)
        self.window_secs = int(window_secs)
        self._log: Dict[str, list] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> Tuple[bool, float]:
        """Return ``(allowed, seconds_until_next_allowed)``.

        ``allowed=False`` means the caller should 429 or return
        ``{"error": "rate_limited"}``. ``seconds_until_next_allowed``
        is the time to wait in seconds (0 when allowed).
        """
        now = time.time()
        cutoff = now - self.window_secs
        with self._lock:
            log = self._log.setdefault(key, [])
            # drop expired
            log[:] = [t for t in log if t >= cutoff]
            if len(log) >= self.max_hits:
                oldest = log[0]
                wait = (oldest + self.window_secs) - now
                return (False, max(0.0, wait))
            log.append(now)
            return (True, 0.0)

    def reset(self, key: str = "") -> None:
        """Clear the log for one key (or all when ``key`` is empty).
        Tests use this for isolation.
        """
        with self._lock:
            if key:
                self._log.pop(key, None)
            else:
                self._log.clear()
