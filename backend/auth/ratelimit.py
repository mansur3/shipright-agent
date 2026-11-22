"""Small in-memory sliding-window rate limiter. One process only; put a shared store behind it if the app runs on several instances."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request, status

_HITS: dict[str, deque] = defaultdict(deque)
ENABLED = True      # tests switch this off; production leaves it on


def reset() -> None:
    _HITS.clear()


def limit(max_calls: int, per_seconds: int, scope: str) -> Callable:
    """FastAPI dependency: at most max_calls per per_seconds for one client (IP) within one scope."""
    def _dep(request: Request) -> None:
        if not ENABLED:
            return
        who = request.client.host if request.client else "unknown"
        q = _HITS[f"{scope}:{who}"]
        now = time.monotonic()
        while q and now - q[0] > per_seconds:
            q.popleft()
        if len(q) >= max_calls:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Try again shortly.",
                                headers={"Retry-After": str(per_seconds)})
        q.append(now)
    return _dep
