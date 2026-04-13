from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.common.exceptions import AppError
from app.common.response import ApiResponse


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = str(uuid.uuid4())[:8]
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except AppError as e:
            return ApiResponse.error(code=e.code, message=e.message)
        except Exception as e:
            return ApiResponse.error(code=500, message=f"internal error: {e}")

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response
