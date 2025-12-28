from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HTTP_429_TOO_MANY_REQUESTS = 429


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and "X-Limit-Remaining" not in response.headers:
            response.headers["X-Limit-Remaining"] = remaining

        if (
            response.status_code == HTTP_429_TOO_MANY_REQUESTS
            and "Retry-After" not in response.headers
        ):
            reset = response.headers.get("X-RateLimit-Reset")
            if reset is not None:
                try:
                    reset_ts = int(float(reset))
                    retry_after = max(0, reset_ts - int(time.time()))
                    response.headers["Retry-After"] = str(retry_after)
                except ValueError:
                    # If reset is malformed, skip adding Retry-After
                    pass

        return response
