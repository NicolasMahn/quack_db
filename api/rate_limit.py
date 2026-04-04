"""Simple in-memory rate limiting middleware."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit request count per client key over a rolling one-minute window."""

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._hits = defaultdict(deque)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        auth_subject = getattr(request.state, "auth_subject", None)
        if auth_subject:
            return f"sub:{auth_subject}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    async def dispatch(self, request: Request, call_next):
        if self.requests_per_minute <= 0:
            return await call_next(request)

        key = self._client_key(request)
        now = time.time()
        cutoff = now - 60
        with self._lock:
            queue = self._hits[key]
            while queue and queue[0] < cutoff:
                queue.popleft()
            if len(queue) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded. Try again in a minute."},
                )
            queue.append(now)

        return await call_next(request)

