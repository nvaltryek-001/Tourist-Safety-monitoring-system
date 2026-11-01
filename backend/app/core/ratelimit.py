"""Small in-process sliding-window rate limiter.

Adequate for a single backend instance (Render free tier). For several
instances, back this with Redis; the interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: float, now: float | None = None) -> bool:
        """Record a hit. Returns True if allowed, False if over the limit."""
        now = time.monotonic() if now is None else now
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def retry_after(self, key: str, window_seconds: float, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        with self._lock:
            bucket = self._hits.get(key)
            if not bucket:
                return 0
            return max(0, int(window_seconds - (now - bucket[0])) + 1)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()
