from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic
from typing import Any

from fastapi import Header, status

from orbitrisk.api.errors import risk_http_exception
from orbitrisk.config import get_settings


@dataclass
class InMemoryRateLimiter:
    window_seconds: float = 60.0
    _hits: dict[str, deque[float]] = field(default_factory=dict)
    _lock: Any = field(default_factory=RLock)

    def allow(self, key: str, *, limit: int, now: float | None = None) -> bool:
        if limit <= 0:
            return False
        current = monotonic() if now is None else now
        window_start = current - self.window_seconds
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= window_start:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(current)
            return True

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


api_rate_limiter = InMemoryRateLimiter()


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    settings = get_settings()
    if x_api_key is None:
        raise risk_http_exception(
            "missing_api_key",
            "Missing X-API-Key header",
            request_id=None,
            status_code=status.HTTP_401_UNAUTHORIZED,
            retryable=False,
        )
    if x_api_key not in settings.api_key_set:
        raise risk_http_exception(
            "invalid_api_key",
            "Invalid API key",
            request_id=None,
            status_code=status.HTTP_403_FORBIDDEN,
            retryable=False,
        )
    if not api_rate_limiter.allow(x_api_key, limit=settings.rate_limit_per_minute):
        raise risk_http_exception(
            "rate_limited",
            "API key rate limit exceeded",
            request_id=None,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            retryable=True,
        )
    return x_api_key
