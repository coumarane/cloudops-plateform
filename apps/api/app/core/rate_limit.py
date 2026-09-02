from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

_HITS: dict[str, deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    _HITS.clear()


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int = 60) -> None:
    now = time.monotonic()
    bucket = _HITS[key]
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Too many credential operations")
    bucket.append(now)
